"use client"

import type React from "react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Minus, Plus } from "lucide-react"

interface QuantityControlProps {
  quantity: number
  onQuantityChange: (newQuantity: number) => void
  min?: number
  max?: number
}

export function QuantityControl({ quantity, onQuantityChange, min = 1, max = 99 }: QuantityControlProps) {
  const handleDecrease = () => {
    if (quantity > min) {
      onQuantityChange(quantity - 1)
    }
  }

  const handleIncrease = () => {
    if (quantity < max) {
      onQuantityChange(quantity + 1)
    }
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = Number.parseInt(e.target.value) || min
    const clampedValue = Math.max(min, Math.min(max, value))
    onQuantityChange(clampedValue)
  }

  return (
    <div className="flex items-center space-x-2">
      <Button
        variant="outline"
        size="icon"
        onClick={handleDecrease}
        disabled={quantity <= min}
        className="h-8 w-8 bg-transparent"
      >
        <Minus className="h-3 w-3" />
      </Button>

      <Input
        type="number"
        value={quantity}
        onChange={handleInputChange}
        min={min}
        max={max}
        className="w-16 h-8 text-center"
      />

      <Button variant="outline" size="icon" onClick={handleIncrease} disabled={quantity >= max} className="h-8 w-8">
        <Plus className="h-3 w-3" />
      </Button>
    </div>
  )
}
