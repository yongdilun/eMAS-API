// Fetches from GET /predictive/confidence
// Expected: { confidence_pct: 85 } OR uses prop fallback
import { useState, useEffect } from 'react'
import { predictiveApi } from '../../../services/api'
import logger from '../../../services/logger'

const ConfidenceLevel = ({ percentage: propPct = 85 }) => {
    const [pct, setPct] = useState(propPct)

    useEffect(() => {
        predictiveApi.confidence()
            .then(data => {
                const v = data?.confidence_pct ?? data?.confidence ?? data?.pct ?? null
                if (v != null) setPct(Number(v))
            })
            .catch((err) => logger.debug('Confidence level API unavailable; using prop fallback', { message: err?.message }))
    }, [])

    const circumference = 2 * Math.PI * 52
    const offset = circumference - (pct / 100) * circumference

    return (
        <div className="flex flex-col items-center justify-center gap-4 rounded-lg border border-hairline bg-surface-1 p-6 text-center">
            <p className="text-lg font-medium text-ink">Model Confidence Level</p>
            <div className="relative flex h-32 w-32 items-center justify-center">
                <svg className="h-full w-full -rotate-90">
                    <circle className="text-surface-3" cx="64" cy="64" fill="transparent" r="52" stroke="currentColor" strokeWidth="10" />
                    <circle className="text-primary" cx="64" cy="64" fill="transparent" r="52" stroke="currentColor"
                        strokeDasharray={circumference} strokeDashoffset={offset} strokeLinecap="round" strokeWidth="10" />
                </svg>
                <span className="absolute text-3xl font-bold text-ink">{pct}%</span>
            </div>
            <p className="text-sm text-ink-subtle">Confidence in current predictions</p>
        </div>
    )
}

export default ConfidenceLevel
