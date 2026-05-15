import { useState, useRef, useEffect, useMemo, useCallback } from 'react'

const SLOTS_PER_DAY = 48 // half-hour slots, 24-hour day (0:00–24:00)
const LEFT_COLUMN_WIDTH = 256
const ROW_HEIGHT = 72
const DAY_HEADER_HEIGHT = 40
const TIME_HEADER_HEIGHT = 36
const HEADER_HEIGHT = DAY_HEADER_HEIGHT + TIME_HEADER_HEIGHT
const JOB_COLOR_SEEDS = [
    { h: 235, s: 56, l: 52 },
    { h: 188, s: 50, l: 38 },
    { h: 148, s: 46, l: 38 },
    { h: 32, s: 62, l: 46 },
    { h: 350, s: 56, l: 48 },
    { h: 268, s: 48, l: 50 },
    { h: 210, s: 58, l: 44 },
    { h: 92, s: 40, l: 36 },
    { h: 14, s: 58, l: 46 },
    { h: 316, s: 46, l: 46 },
    { h: 172, s: 46, l: 34 },
    { h: 45, s: 62, l: 42 },
    { h: 225, s: 46, l: 42 },
    { h: 132, s: 40, l: 38 },
    { h: 286, s: 44, l: 46 },
    { h: 6, s: 56, l: 46 },
]

function jobColorsForIndex(index) {
    const seed = JOB_COLOR_SEEDS[index % JOB_COLOR_SEEDS.length]
    const cycle = Math.floor(index / JOB_COLOR_SEEDS.length)
    const hue = (seed.h + cycle * 17) % 360
    const saturation = Math.max(38, seed.s - Math.min(cycle, 5) * 2)
    const lightness = Math.max(34, Math.min(52, seed.l + ((cycle % 3) - 1) * 3))

    return {
        bg: `hsl(${hue} ${saturation}% ${lightness}%)`,
        light: `hsl(${hue} ${Math.max(30, saturation - 12)}% ${Math.min(92, lightness + 34)}% / 0.18)`,
        border: `hsl(${hue} ${Math.min(82, saturation + 12)}% ${Math.max(28, lightness - 14)}%)`,
    }
}

function sameSlot(a, b) {
    if (!a || !b) return false
    const aSlotId = a.slot_id || a.slotId
    const bSlotId = b.slot_id || b.slotId
    if (aSlotId && bSlotId) return String(aSlotId) === String(bSlotId)

    const aStepId = a.job_step_id || a.jobStepId || a.step_id || a.stepId
    const bStepId = b.job_step_id || b.jobStepId || b.step_id || b.stepId
    const aMachine = a.machine_id || a.machineId
    const bMachine = b.machine_id || b.machineId
    const aStart = a.scheduled_start || a.scheduledStart || a.start_time
    const bStart = b.scheduled_start || b.scheduledStart || b.start_time

    return String(aMachine || '') === String(bMachine || '') &&
        String(aStart || '') === String(bStart || '') &&
        (!aStepId || !bStepId || String(aStepId) === String(bStepId))
}

function buildSmoothFlowPath(points) {
    if (!points || points.length < 2) return ''
    const [first, ...rest] = points
    return rest.reduce((path, point, index) => {
        const prev = points[index]
        const midX = (prev.x + point.x) / 2
        return `${path} C ${midX} ${prev.y}, ${midX} ${point.y}, ${point.x} ${point.y}`
    }, `M ${first.x} ${first.y}`)
}

/** Convert ISO start/end to position using continuous time (no slot snapping). Prevents overlap for adjacent slots (e.g. 10:57–12:57, 12:57–14:57). */
function slotToPosition(scheduled_start, scheduled_end, baseDate, totalSpanMs) {
    const baseMs = baseDate.getTime()
    const startDate = scheduled_start ? new Date(scheduled_start) : baseDate
    const endDate = scheduled_end ? new Date(scheduled_end) : startDate

    const startMs = startDate.getTime()
    const endMs = Math.max(endDate.getTime(), startMs + 60000)

    const span = Math.max(totalSpanMs, 86400000)
    const leftPct = Math.max(0, Math.min(100, ((startMs - baseMs) / span) * 100))
    const widthPct = Math.max(0, Math.min(100 - leftPct, ((endMs - startMs) / span) * 100))

    const startDayOffset = Math.floor((startMs - baseMs) / 86400000)
    const endDayOffset = Math.floor((endMs - baseMs) / 86400000)
    const startHour = startDate.getHours()
    const startMin = startDate.getMinutes()
    const startSlotInDay = Math.max(0, Math.min(47, startHour * 2 + Math.floor(startMin / 30)))
    const endHour = endDate.getHours()
    const endMin = endDate.getMinutes()
    const endSlotInDay = Math.min(SLOTS_PER_DAY, endHour * 2 + Math.ceil(endMin / 30))
    const absStartSlot = startDayOffset * SLOTS_PER_DAY + startSlotInDay
    const absEndSlot = endDayOffset * SLOTS_PER_DAY + endSlotInDay

    return {
        dayOffset: startDayOffset,
        startSlot: startSlotInDay,
        endSlot: absEndSlot - startDayOffset * SLOTS_PER_DAY,
        absStartSlot,
        absEndSlot,
        leftPct,
        widthPct,
    }
}

const GanttTable = ({ jobs = [], machines: machinesProp = [], selectedJobId: selectedJobIdProp, selectedSlot = null, onJobClick, isPreview = false }) => {
    const [internalSelected, setInternalSelected] = useState(null)
    const selectedJobId = selectedJobIdProp !== undefined ? selectedJobIdProp : internalSelected
    const setSelectedJobId = (id) => {
        setInternalSelected(id)
    }
    const [zoomLevel, setZoomLevel] = useState(1)
    const headerScrollRef = useRef(null)
    const bodyScrollRef = useRef(null)
    const canvasRef = useRef(null)

    const now = useMemo(() => new Date(), [])
    const zoomLevels = [
        { label: '4 Hour', hours: 4, width: 400 },
        { label: '2 Hour', hours: 2, width: 600 },
        { label: '1 Hour', hours: 1, width: 1200 },
        { label: '30 Min', hours: 0.5, width: 2400 },
    ]
    const currentZoom = zoomLevels[zoomLevel]

    const jobColorMap = useMemo(() => {
        const map = new Map()
        let colorIndex = 0

        jobs.forEach((job) => {
            const jobId = job.job_id || job.jobId || job.id
            if (!jobId || map.has(jobId)) return
            map.set(jobId, jobColorsForIndex(colorIndex))
            colorIndex += 1
        })

        return map
    }, [jobs])

    const { machineRows, displaySlots, totalDays, startDate, baseDate } = useMemo(() => {
        const allSlots = []
        jobs.forEach((job, jobIdx) => {
            (job.slots || []).forEach((slot) => {
                const mid = slot.machine_id || slot.machineId || '—'
                allSlots.push({
                    ...slot,
                    job,
                    jobIdx,
                    machineId: mid,
                })
            })
        })

        const machineIds = [...new Set(allSlots.map((s) => s.machineId).filter(Boolean))]
        const machineMap = new Map()
            ; (machinesProp.length ? machinesProp : machineIds.map((id) => ({ machine_id: id, machine_name: id }))).forEach((m, i) => {
                const mid = m.machine_id || m.machineId || m.id || String(i)
                if (!machineMap.has(mid)) machineMap.set(mid, m.machine_name || m.machineName || mid)
            })
        machineIds.forEach((id) => { if (!machineMap.has(id)) machineMap.set(id, id) })

        const machineRows = machineIds.length ? machineIds : [...machineMap.keys()]
        const machineLabel = (id) => machineMap.get(id) || id

        let minDate = null
        let maxDate = null
        allSlots.forEach((s) => {
            const start = s.scheduled_start ? new Date(s.scheduled_start) : null
            const end = s.scheduled_end ? new Date(s.scheduled_end) : null
            if (start) { if (!minDate || start < minDate) minDate = new Date(start) }
            if (end) { if (!maxDate || end > maxDate) maxDate = new Date(end) }
        })

        const refDate = minDate || now
        const baseDate = new Date(refDate)
        baseDate.setHours(0, 0, 0, 0)

        const maxEnd = maxDate || new Date(refDate.getTime() + 7 * 86400000)
        const daysSpan = Math.max(1, Math.ceil((maxEnd.getTime() - baseDate.getTime()) / 86400000))
        const totalDays = Math.max(7, daysSpan + 2)
        const startDate = baseDate
        const totalSpanMs = totalDays * 86400000

        const displaySlots = allSlots.map((s) => {
            const pos = slotToPosition(s.scheduled_start, s.scheduled_end, baseDate, totalSpanMs)
            const actualPos = (s.actual_start && s.actual_end)
                ? slotToPosition(s.actual_start, s.actual_end, baseDate, totalSpanMs)
                : null
            return {
                ...s,
                ...pos,
                actualLeftPct: actualPos?.leftPct,
                actualWidthPct: actualPos?.widthPct,
                machineLabel: machineLabel(s.machineId),
            }
        })

        return { machineRows, displaySlots, totalDays, startDate, baseDate }
    }, [jobs, machinesProp, now])

    const dayWidth = currentZoom.width
    const totalSlots = totalDays * SLOTS_PER_DAY
    const timelineWidth = totalDays * dayWidth

    const formatDate = (date) => {
        const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        return `${months[date.getMonth()]} ${date.getDate()}`
    }

    const generateTimeSlots = useCallback(() => {
        const slots = []
        const slotsPerZoom = Math.max(1, currentZoom.hours * 2)
        for (let day = 0; day < totalDays; day++) {
            const currentDate = new Date(startDate)
            currentDate.setDate(currentDate.getDate() + day)
            for (let slot = 0; slot < SLOTS_PER_DAY; slot += slotsPerZoom) {
                if (slot >= SLOTS_PER_DAY) break
                const hour = slot * 0.5
                const h = Math.floor(hour)
                const m = (slot % 2) * 30
                const label = m === 0 ? `${h.toString().padStart(2, '0')}:00` : `${h.toString().padStart(2, '0')}:30`
                slots.push({ day, slot, date: currentDate, label })
            }
        }
        return slots
    }, [currentZoom.hours, startDate, totalDays])

    const timeSlots = useMemo(() => generateTimeSlots(), [generateTimeSlots])
    const timeSlotsByDay = useMemo(() => {
        const grouped = new Map()
        timeSlots.forEach((slot) => {
            if (!grouped.has(slot.day)) grouped.set(slot.day, [])
            grouped.get(slot.day).push(slot)
        })
        return grouped
    }, [timeSlots])

    const getCurrentSlot = () => {
        const baseMs = baseDate.getTime()
        const dayMs = 86400000
        const daysDiff = Math.floor((now.getTime() - baseMs) / dayMs)
        const hours = now.getHours()
        const minutes = now.getMinutes()
        const slotInDay = hours * 2 + Math.floor(minutes / 30)
        return Math.max(0, daysDiff * SLOTS_PER_DAY + slotInDay)
    }

    const currentSlot = getCurrentSlot()
    const currentSlotPosition = (currentSlot / totalSlots) * 100

    const calculateSlotPosition = useCallback((dayOffset, startSlot) => {
        const absSlot = dayOffset * SLOTS_PER_DAY + startSlot
        return (absSlot / totalSlots) * 100
    }, [totalSlots])

    const calculateSlotWidth = useCallback((dayOffset, startSlot, endSlot) => {
        const absStart = dayOffset * SLOTS_PER_DAY + startSlot
        const absEnd = dayOffset * SLOTS_PER_DAY + (endSlot || startSlot + 1)
        return ((absEnd - absStart) / totalSlots) * 100
    }, [totalSlots])

    const isStepPast = (dayOffset, endSlot) => {
        const absEnd = dayOffset * SLOTS_PER_DAY + (endSlot || 0)
        return absEnd <= currentSlot
    }

    const selectedJobFlowPath = useMemo(() => {
        if (!selectedJobId) return ''
        const points = displaySlots
            .filter((slot) => {
                const jobId = slot.job?.job_id || slot.job?.jobId || slot.job?.id
                return String(jobId || '') === String(selectedJobId)
            })
            .sort((a, b) => {
                const aStart = new Date(a.scheduled_start || a.scheduledStart || a.start_time || 0).getTime()
                const bStart = new Date(b.scheduled_start || b.scheduledStart || b.start_time || 0).getTime()
                if (aStart !== bStart) return aStart - bStart
                const aSeq = a.step_sequence ?? a.stepSequence ?? a.jobIdx ?? 0
                const bSeq = b.step_sequence ?? b.stepSequence ?? b.jobIdx ?? 0
                return Number(aSeq) - Number(bSeq)
            })
            .map((slot) => {
                const rowIndex = machineRows.findIndex((machineId) => String(machineId) === String(slot.machineId))
                if (rowIndex < 0) return null
                const leftPct = slot.leftPct ?? calculateSlotPosition(slot.dayOffset, slot.startSlot)
                const widthPct = slot.widthPct ?? calculateSlotWidth(slot.dayOffset, slot.startSlot, slot.endSlot)
                return {
                    x: ((leftPct + widthPct / 2) / 100) * timelineWidth,
                    y: rowIndex * ROW_HEIGHT + ROW_HEIGHT / 2,
                }
            })
            .filter(Boolean)

        return buildSmoothFlowPath(points)
    }, [selectedJobId, displaySlots, machineRows, timelineWidth, calculateSlotPosition, calculateSlotWidth])

    const handleSlotClick = (displaySlot) => {
        const job = displaySlot.job
        const jobId = job.job_id || job.jobId || job.id
        setSelectedJobId(jobId)
        onJobClick?.({ job, clickedSlot: displaySlot })
    }

    useEffect(() => {
        const headerEl = headerScrollRef.current
        const bodyEl = bodyScrollRef.current
        if (!headerEl || !bodyEl) return
        let isHeaderScrolling = false
        let isBodyScrolling = false
        const syncHeader = () => {
            if (!isBodyScrolling) {
                isHeaderScrolling = true
                headerEl.scrollLeft = bodyEl.scrollLeft
                setTimeout(() => { isHeaderScrolling = false }, 10)
            }
        }
        const syncBody = () => {
            if (!isHeaderScrolling) {
                isBodyScrolling = true
                bodyEl.scrollLeft = headerEl.scrollLeft
                setTimeout(() => { isBodyScrolling = false }, 10)
            }
        }
        bodyEl.addEventListener('scroll', syncHeader)
        headerEl.addEventListener('scroll', syncBody)
        return () => {
            bodyEl.removeEventListener('scroll', syncHeader)
            headerEl.removeEventListener('scroll', syncBody)
        }
    }, [zoomLevel])

    useEffect(() => {
        if (!selectedSlot || !bodyScrollRef.current) return
        const rowIndex = machineRows.findIndex((machineId) =>
            String(machineId) === String(selectedSlot.machine_id || selectedSlot.machineId)
        )
        const positionedSlot = displaySlots.find((slot) => sameSlot(slot, selectedSlot))
        if (rowIndex < 0 || !positionedSlot) return

        const bodyEl = bodyScrollRef.current
        const targetLeft = (positionedSlot.leftPct / 100) * timelineWidth
        const targetTop = rowIndex * ROW_HEIGHT
        const centeredLeft = Math.max(0, targetLeft - bodyEl.clientWidth * 0.35)
        const centeredTop = Math.max(0, targetTop - bodyEl.clientHeight * 0.35)

        bodyEl.scrollTo({
            left: centeredLeft,
            top: centeredTop,
            behavior: 'smooth',
        })
    }, [selectedSlot, displaySlots, machineRows, timelineWidth])

    const getDateForDay = (dayOffset) => {
        const d = new Date(startDate)
        d.setDate(d.getDate() + dayOffset)
        return d
    }

    const isToday = (date) =>
        date.getDate() === now.getDate() && date.getMonth() === now.getMonth() && date.getFullYear() === now.getFullYear()

    const getMachineLabel = (machineId) => {
        const m = machinesProp.find((x) => (x.machine_id || x.machineId || x.id) === machineId)
        return m?.machine_name || m?.machineName || machineId || '—'
    }

    return (
        <div className="relative flex h-full min-h-0 flex-col">
            <div className="mb-4 flex flex-shrink-0 items-center justify-between gap-4 rounded-lg border border-hairline bg-surface-1 px-4 py-3">
                <div>
                    <p className="text-sm font-semibold text-ink">Scheduling Grid</p>
                    <p className="mt-0.5 text-xs text-ink-subtle">{machineRows.length} resources across {totalDays} days</p>
                </div>
                <div className="flex items-center gap-2 rounded-md border border-hairline bg-canvas p-1">
                    <span className="px-2 text-caption font-medium text-ink-subtle">
                        <span className="material-symbols-outlined mr-1 align-[-3px] text-base">zoom_in</span>
                        Zoom
                    </span>
                    {zoomLevels.map((level, idx) => (
                        <button
                            key={idx}
                            onClick={() => setZoomLevel(idx)}
                            className={`h-8 rounded-md px-3 text-button transition-colors ${zoomLevel === idx ? 'bg-primary text-on-primary' : 'text-ink-subtle hover:bg-surface-2 hover:text-ink'
                                }`}
                        >
                            {level.label}
                        </button>
                    ))}
                </div>
            </div>

            <div className={`flex min-h-0 flex-1 flex-col overflow-hidden rounded-xl border bg-canvas ${isPreview ? 'border-primary/50 border-dashed' : 'border-hairline'}`}>
                <div className="sticky top-0 z-50 flex-shrink-0 border-b border-hairline bg-canvas">
                    <div className="flex">
                        <div
                            className="z-50 flex flex-shrink-0 items-center border-r border-hairline bg-surface-1 px-4 text-sm font-semibold text-ink"
                            style={{ width: LEFT_COLUMN_WIDTH, height: HEADER_HEIGHT }}
                        >
                            <span className="material-symbols-outlined mr-2 text-base text-ink-subtle">precision_manufacturing</span>
                            <span>Machine / Resource</span>
                        </div>
                        <div className="flex-1 overflow-hidden" ref={headerScrollRef}>
                            <div key={`gantt-header-${zoomLevel}`} className="gantt-zoom-surface flex" style={{ width: timelineWidth, minWidth: timelineWidth }}>
                                {Array.from({ length: totalDays }).map((_, dayIndex) => {
                                    const dayDate = getDateForDay(dayIndex)
                                    const isTodayDate = isToday(dayDate)
                                    return (
                                        <div key={dayIndex} className="flex-shrink-0 border-r border-hairline" style={{ width: dayWidth }}>
                                            <div
                                                className={`flex items-center justify-center border-b border-hairline px-3 text-sm font-semibold ${isTodayDate ? 'bg-surface-3 text-ink' : 'bg-surface-1 text-ink-muted'
                                                    }`}
                                                style={{ height: DAY_HEADER_HEIGHT }}
                                            >
                                                {formatDate(dayDate)} {isTodayDate && '(Today)'}
                                            </div>
                                            <div className="flex">
                                                {(timeSlotsByDay.get(dayIndex) || []).map((slot, idx) => (
                                                    <div
                                                        key={idx}
                                                        className="flex flex-1 items-center justify-center border-r border-hairline px-2 text-caption font-medium text-ink-subtle last:border-r-0"
                                                        style={{ height: TIME_HEADER_HEIGHT }}
                                                    >
                                                        {slot.label}
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )
                                })}
                            </div>
                        </div>
                    </div>
                </div>

                <div className="flex-1 overflow-x-auto overflow-y-auto" ref={bodyScrollRef}>
                    <div className="relative" style={{ minHeight: `${machineRows.length * ROW_HEIGHT}px`, minWidth: `${timelineWidth + LEFT_COLUMN_WIDTH}px` }}>
                        <div className="flex">
                            <div className="sticky left-0 z-40 flex-shrink-0 border-r border-hairline bg-surface-1" style={{ width: LEFT_COLUMN_WIDTH }}>
                                {machineRows.map((machineId) => (
                                    <div
                                        key={machineId}
                                        className="flex items-center border-b border-hairline bg-surface-1 px-4 text-sm font-medium text-ink"
                                        style={{ height: ROW_HEIGHT }}
                                    >
                                        <span className="material-symbols-outlined mr-3 text-base text-primary">precision_manufacturing</span>
                                        <span className="truncate">{getMachineLabel(machineId)}</span>
                                    </div>
                                ))}
                            </div>

                            <div key={`gantt-body-${zoomLevel}`} className="gantt-zoom-surface relative flex-shrink-0" style={{ width: timelineWidth }}>
                                <canvas ref={canvasRef} className="pointer-events-none absolute left-0 top-0 z-20" style={{ width: timelineWidth, height: machineRows.length * ROW_HEIGHT }} />
                                {selectedJobFlowPath && (
                                    <svg
                                        className="gantt-job-flow pointer-events-none absolute left-0 top-0 z-[6]"
                                        width={timelineWidth}
                                        height={machineRows.length * ROW_HEIGHT}
                                        viewBox={`0 0 ${timelineWidth} ${machineRows.length * ROW_HEIGHT}`}
                                        preserveAspectRatio="none"
                                        aria-hidden="true"
                                    >
                                        <defs>
                                            <marker
                                                id={`gantt-flow-arrow-${isPreview ? 'preview' : 'applied'}`}
                                                markerWidth="8"
                                                markerHeight="8"
                                                refX="7"
                                                refY="4"
                                                orient="auto"
                                                markerUnits="strokeWidth"
                                            >
                                                <path className="gantt-job-flow-arrow" d="M 0 0 L 8 4 L 0 8 z" />
                                            </marker>
                                        </defs>
                                        <path
                                            className="gantt-job-flow-path"
                                            d={selectedJobFlowPath}
                                            markerEnd={`url(#gantt-flow-arrow-${isPreview ? 'preview' : 'applied'})`}
                                        />
                                    </svg>
                                )}

                                {machineRows.map((machineId, machineIndex) => {
                                    const slotsOnMachine = displaySlots.filter((s) => s.machineId === machineId)
                                    return (
                                        <div
                                            key={machineId}
                                            className="relative border-b border-hairline bg-canvas transition-colors hover:bg-surface-1"
                                            style={{ height: ROW_HEIGHT }}
                                        >
                                            <div className="absolute inset-0 flex">
                                                {Array.from({ length: totalDays }).map((_, dayIdx) => (
                                                    <div key={dayIdx} className="gantt-grid-day relative flex-1 border-r">
                                                        {Array.from({ length: SLOTS_PER_DAY }).map((_, slotIdx) => (
                                                            <div
                                                                key={slotIdx}
                                                                className={`absolute bottom-0 top-0 border-r ${slotIdx % 4 === 0 ? 'gantt-grid-major' : slotIdx % 2 === 0 ? 'gantt-grid-hour' : 'gantt-grid-minor'}`}
                                                                style={{ left: `${(slotIdx / SLOTS_PER_DAY) * 100}%` }}
                                                            />
                                                        ))}
                                                    </div>
                                                ))}
                                            </div>

                                            {machineIndex === 0 && currentSlotPosition > 0 && currentSlotPosition < 100 && (
                                                <div className="absolute top-0 z-[15]" style={{ left: `${currentSlotPosition}%`, height: `${machineRows.length * ROW_HEIGHT}px` }}>
                                                    <div className="h-full w-px bg-primary" />
                                                </div>
                                            )}

                                            <div
                                                className="pointer-events-none absolute bottom-0 top-0 z-[1] bg-surface-2/45"
                                                style={{ left: 0, width: `${currentSlotPosition}%` }}
                                            />

                                            {slotsOnMachine.map((displaySlot, slotIdx) => {
                                                const job = displaySlot.job
                                                const jobId = job.job_id || job.jobId || job.id
                                                const colors =
                                                    (jobId && jobColorMap.get(jobId)) ||
                                                    { bg: '#5e6ad2', light: 'rgba(94, 106, 210, 0.14)', border: '#828fff' }
                                                const isSelected = selectedJobId === jobId
                                                const isSelectedStep = isSelected && sameSlot(displaySlot, selectedSlot)
                                                const isOtherSelectedJobStep = isSelected && selectedSlot && !isSelectedStep
                                                const completed = displaySlot.status === 'completed'
                                                const running = displaySlot.status === 'running' || displaySlot.status === 'in-progress'
                                                const paused = displaySlot.status === 'paused'
                                                const stepIsPast = isStepPast(displaySlot.dayOffset, displaySlot.endSlot)
                                                const textStyle = { color: '#ffffff' }

                                                const leftPct = displaySlot.leftPct ?? calculateSlotPosition(displaySlot.dayOffset, displaySlot.startSlot)
                                                const widthPct = displaySlot.widthPct ?? calculateSlotWidth(displaySlot.dayOffset, displaySlot.startSlot, displaySlot.endSlot)
                                                const stepWidth = (widthPct / 100) * timelineWidth
                                                const hasActualOverlay = (running || completed) && displaySlot.actualLeftPct != null && displaySlot.actualWidthPct != null

                                                const slotLeft = hasActualOverlay ? Math.min(leftPct, displaySlot.actualLeftPct) : leftPct
                                                const slotRight = hasActualOverlay ? Math.max(leftPct + widthPct, displaySlot.actualLeftPct + displaySlot.actualWidthPct) : leftPct + widthPct
                                                const slotWidth = slotRight - slotLeft

                                                const showFullContent = stepWidth > 120
                                                const showMinimal = stepWidth > 80 && stepWidth <= 120
                                                const showNothing = stepWidth <= 50
                                                const showLateBadge = stepWidth > 150 && (job.deadline_status?.is_late || job.deadline_status?.isLate)

                                                return (
                                                    <div
                                                        key={`${jobId}-${displaySlot.slot_id || slotIdx}`}
                                                        className={`absolute left-0 top-2 h-14 cursor-pointer overflow-visible rounded-lg transition-colors hover:ring-2 hover:ring-primary/40 hover:ring-offset-1 hover:ring-offset-canvas ${isSelectedStep
                                                                ? 'z-40 ring-2 ring-primary ring-offset-2 ring-offset-canvas'
                                                                : isOtherSelectedJobStep
                                                                    ? 'z-20 ring-1 ring-primary/35'
                                                                    : isSelected
                                                                        ? 'z-30 ring-2 ring-primary/70 ring-offset-1 ring-offset-canvas'
                                                                        : 'z-10'
                                                            }`}
                                                        style={{
                                                            left: `${slotLeft}%`,
                                                            width: `max(6px, ${slotWidth}%)`,
                                                        }}
                                                        onClick={() => handleSlotClick(displaySlot)}
                                                    >
                                                        {/* Planned bar (dashed when actual overlay present) */}
                                                        <div
                                                            className="absolute inset-0 rounded-lg border border-white/10"
                                                            style={{
                                                                left: hasActualOverlay ? `${((leftPct - slotLeft) / slotWidth) * 100}%` : 0,
                                                                width: hasActualOverlay ? `${(widthPct / slotWidth) * 100}%` : '100%',
                                                                backgroundColor: stepIsPast && !completed ? colors.light
                                                                    : paused ? `color-mix(in srgb, ${colors.bg} 70%, #92400e)`
                                                                        : running ? `color-mix(in srgb, ${colors.bg} 90%, #f59e0b)`
                                                                            : colors.bg,
                                                                borderLeft: `3px ${hasActualOverlay || paused ? 'dashed' : 'solid'} ${paused ? '#d97706' : running ? '#f59e0b' : colors.border}`,
                                                                opacity: hasActualOverlay ? 0.5 : 1,
                                                                filter: isOtherSelectedJobStep ? 'saturate(0.72) brightness(0.74)' : (stepIsPast && !completed ? 'grayscale(0.35) brightness(0.8)' : 'none'),
                                                            }}
                                                        />
                                                        {/* Actual bar overlay (solid) */}
                                                        {hasActualOverlay && (
                                                            <div
                                                                className="absolute bottom-0 top-0 z-[1] rounded-lg"
                                                                style={{
                                                                    left: `${((displaySlot.actualLeftPct - slotLeft) / slotWidth) * 100}%`,
                                                                    width: `${(displaySlot.actualWidthPct / slotWidth) * 100}%`,
                                                                    backgroundColor: completed ? colors.bg : `color-mix(in srgb, ${colors.bg} 95%, #f59e0b)`,
                                                                    borderLeft: `3px solid ${completed ? colors.border : '#f59e0b'}`,
                                                                }}
                                                            />
                                                        )}
                                                        {isSelectedStep && (
                                                            <div className="absolute -inset-1 z-[2] rounded-lg border-2 border-primary" />
                                                        )}
                                                        {isOtherSelectedJobStep && (
                                                            <div className="absolute inset-0 z-[2] rounded-lg border border-primary/35 bg-canvas/20" />
                                                        )}
                                                        {showLateBadge && (
                                                            <span
                                                                className="absolute right-1.5 top-1.5 z-20 rounded-md border border-white/20 bg-canvas/90 px-1.5 py-0.5 text-[9px] font-semibold text-ink-muted backdrop-blur-[1px]"
                                                                title={`Late by ${job.deadline_status?.late_by || job.deadline_status?.lateBy || ''}`}
                                                            >
                                                                Late
                                                            </span>
                                                        )}
                                                        {!showNothing && (
                                                            <div className="relative z-[2] flex h-full flex-col justify-center overflow-hidden px-2.5 py-1.5">
                                                                <div className="flex min-w-0 items-center gap-1">
                                                                    <span className="min-w-0 truncate text-xs font-semibold" style={textStyle}>
                                                                        {jobId || job.product_id || '—'}
                                                                    </span>
                                                                    {showFullContent && (
                                                                        <span className="shrink-0 truncate text-xs font-medium opacity-90" style={textStyle}>
                                                                            {completed && <span className="material-symbols-outlined text-sm mr-1 align-middle">check_circle</span>}
                                                                            {job.product_id || ''}
                                                                        </span>
                                                                    )}
                                                                </div>
                                                                {showFullContent && (
                                                                    <span className="truncate text-xs font-medium opacity-80" style={textStyle}>{job.product_id || jobId}</span>
                                                                )}
                                                                {showMinimal && !showFullContent && (
                                                                    <span className="truncate text-xs font-medium opacity-80" style={textStyle}>{job.product_id || jobId}</span>
                                                                )}
                                                            </div>
                                                        )}
                                                    </div>
                                                )
                                            })}
                                        </div>
                                    )
                                })}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}

export default GanttTable
