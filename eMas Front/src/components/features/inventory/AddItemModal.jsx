import { useState, useEffect } from 'react'
import { inventoryApi, referenceApi, toData } from '../../../services/api'
import RefSelect from '../../shared/RefSelect'

const EMPTY = { materialName: '', materialId: '', unit: 'kg', currentStock: '', minStock: '', storageLocation: '' }

const AddItemModal = ({ isOpen, onClose, onSave, item }) => {
    const isEdit = !!item
    const [formData, setFormData] = useState(EMPTY)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')

    useEffect(() => {
        if (!isOpen) return
        if (item) {
            setFormData({
                materialName: item.material_name || item.name || '',
                materialId: item.material_id || item.id || '',
                unit: item.unit || 'kg',
                currentStock: item.current_stock ?? item.currentStock ?? '',
                minStock: item.min_stock ?? item.minStock ?? '',
                storageLocation: item.storage_location || item.storage_area || item.storageArea || '',
            })
        } else {
            setFormData(EMPTY)
        }
        setError('')
    }, [isOpen, item])

    const handleChange = (e) => {
        const { name, value } = e.target
        setFormData((prev) => ({ ...prev, [name]: value }))
    }

    const handleSubmit = async () => {
        if (!formData.materialName) {
            setError('Material Name is required.')
            return
        }
        setLoading(true); setError('')

        const payload = {
            ...(formData.materialId ? { material_id: formData.materialId } : {}),
            material_name: formData.materialName,
            unit: formData.unit,
            current_stock: parseFloat(formData.currentStock) || 0,
            min_stock: parseFloat(formData.minStock) || 0,
            storage_location: formData.storageLocation || undefined, // API field: storage_location
        }

        try {
            if (isEdit) {
                // Use PUT if available, otherwise re-create
                const raw = await inventoryApi.update?.(formData.materialId, payload) ?? await inventoryApi.create(payload)
                const saved = toData(raw) ?? raw ?? payload
                if (onSave) onSave(saved)
            } else {
                const raw = await inventoryApi.create(payload)
                const saved = toData(raw) ?? raw ?? payload
                if (onSave) onSave(saved)
            }
            setFormData(EMPTY)
            onClose()
        } catch (err) {
            setError(err.message || 'Failed to save. Please try again.')
        } finally {
            setLoading(false)
        }
    }

    const handleCancel = () => { setFormData(EMPTY); setError(''); onClose() }

    if (!isOpen) return null

    const inp = 'w-full px-4 py-2.5 rounded-lg bg-surface-1 border border-hairline focus:ring-2 focus:ring-primary focus:border-primary transition-all text-sm placeholder-gray-500 dark:placeholder-gray-400 text-ink focus:outline-none'

    return (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50">
            <div className="w-full max-w-2xl bg-surface-1 border border-hairline rounded-xl -2xl">
                <div className="p-6 border-b border-hairline">
                    <h2 className="text-xl font-semibold text-ink">
                        {isEdit ? 'Edit Inventory Item' : 'Add New Inventory Item'}
                    </h2>
                    <p className="text-sm text-ink-subtle mt-1">
                        {isEdit ? 'Update material details.' : 'Register a new material in inventory.'}
                    </p>
                </div>
                <div className="p-6">
                    {error && (
                        <div className="mb-4 flex items-center gap-2 px-3 py-2 bg-red-50 border border-red-200 dark:border-red-800 rounded-lg text-sm text-ink-muted">
                            <span className="material-symbols-outlined text-base">error</span>{error}
                        </div>
                    )}
                    <form className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="md:col-span-2">
                            <label className="block text-sm font-medium text-ink-muted mb-2" htmlFor="materialName">Material Name *</label>
                            <input className={inp} id="materialName" name="materialName" value={formData.materialName} onChange={handleChange} placeholder="e.g., Aluminum Alloy 6061" type="text" />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-ink-muted mb-2" htmlFor="materialId">Material ID</label>
                            <input className={inp} id="materialId" name="materialId" value={formData.materialId} onChange={handleChange} placeholder="Generated when blank" type="text" disabled={isEdit} />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-ink-muted mb-2" htmlFor="unit">Unit</label>
                            <select className={inp} id="unit" name="unit" value={formData.unit} onChange={handleChange}>
                                {['kg', 'pcs', 'L', 'm', 'units', 'set'].map(u => <option key={u} className="bg-surface-1">{u}</option>)}
                            </select>
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-ink-muted mb-2" htmlFor="currentStock">Current Stock</label>
                            <input className={inp} id="currentStock" name="currentStock" value={formData.currentStock} onChange={handleChange} placeholder="0" type="number" min="0" step="0.01" />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-ink-muted mb-2" htmlFor="minStock">Minimum Required Stock</label>
                            <input className={inp} id="minStock" name="minStock" value={formData.minStock} onChange={handleChange} placeholder="0" type="number" min="0" step="0.01" />
                        </div>
                        <div className="md:col-span-2">
                            <label className="block text-sm font-medium text-ink-muted mb-2">Storage Location</label>
                            <RefSelect
                                className={inp}
                                name="storageLocation"
                                value={formData.storageLocation}
                                onChange={(v) => setFormData(p => ({ ...p, storageLocation: v }))}
                                fetcher={referenceApi.storageLocations.list}
                                placeholder="Select storage location…"
                                allowCustom
                            />
                        </div>
                    </form>
                </div>
                <div className="p-6 bg-surface-2 border-t border-hairline flex justify-end gap-4 rounded-b-xl">
                    <button onClick={handleCancel} className="px-5 py-2.5 text-sm font-semibold rounded-lg text-ink-muted hover:bg-gray-200 transition-all">Cancel</button>
                    <button onClick={handleSubmit} disabled={loading} className="px-5 py-2.5 text-sm font-semibold bg-primary text-white rounded-lg hover:bg-primary/90 transition-all flex items-center gap-2 disabled:opacity-60">
                        {loading ? <><span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />Saving…</> : isEdit ? 'Update Item' : 'Save Item'}
                    </button>
                </div>
            </div>
        </div>
    )
}

export default AddItemModal
