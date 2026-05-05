import { useState, useCallback } from 'react'

const useLocalStorage = (key, initialValue) => {
  const [storedValue, setStoredValue] = useState(() => {
    try {
      const item = window.localStorage.getItem(key)
      return item ? JSON.parse(item) : initialValue
    } catch (error) {
      return initialValue
    }
  })

  const setValue = useCallback((value) => {
    try {
      setStoredValue((prev) => {
        const newValue = value instanceof Function ? value(prev) : value
        window.localStorage.setItem(key, JSON.stringify(newValue))
        return newValue
      })
    } catch (error) {
      console.error(error)
    }
  }, [key])

  return [storedValue, setValue]
}

export default useLocalStorage


