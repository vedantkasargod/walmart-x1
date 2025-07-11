"use client"

import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ShoppingCart, X } from "lucide-react"
import { useCartStore } from "@/hooks/useCartStore"
import Image from "next/image"
import { useState } from "react"

interface CartSidebarProps {
  onRemoveItem: (itemId: string) => void
  onCheckout: () => void
}

export function CartSidebar({ onRemoveItem, onCheckout }: CartSidebarProps) {
  const { items, totalPrice } = useCartStore()
  const [isOpen, setIsOpen] = useState(false)

  const totalItems = items.reduce((sum, item) => sum + item.quantity, 0)

  const handleCheckout = () => {
    setIsOpen(false) // Close the sidebar
    onCheckout() // Trigger the payment modal
  }

  return (
    <Sheet open={isOpen} onOpenChange={setIsOpen}>
      <SheetTrigger asChild>
        <Button variant="ghost" className="relative p-2">
          <ShoppingCart className="w-6 h-6" />
          {totalItems > 0 && (
            <Badge className="absolute -top-1 -right-1 bg-yellow-400 text-black text-xs min-w-[20px] h-5 flex items-center justify-center rounded-full">
              {totalItems}
            </Badge>
          )}
        </Button>
      </SheetTrigger>

      <SheetContent className="w-[400px] sm:w-[540px]">
        <SheetHeader>
          <SheetTitle className="text-xl font-bold">Your Smart Cart</SheetTitle>
        </SheetHeader>

        <div className="mt-6 flex flex-col h-full">
          {items.length === 0 ? (
            <div className="flex-1 flex items-center justify-center text-gray-500">
              <div className="text-center">
                <ShoppingCart className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p>Your cart is empty</p>
                <p className="text-sm">Use Smart Search to add items!</p>
              </div>
            </div>
          ) : (
            <>
              <div className="flex-1 overflow-y-auto space-y-4">
                {items.map((item) => (
                  <div key={item.item_id} className="flex items-center space-x-4 p-4 border rounded-lg">
                    <Image
                      src={item.image_url || "/placeholder.svg?height=60&width=60"}
                      alt={item.name}
                      width={60}
                      height={60}
                      className="rounded-md object-cover"
                    />

                    <div className="flex-1 min-w-0">
                      <h3 className="font-medium text-sm leading-tight">{item.name}</h3>
                      <div className="flex items-center justify-between mt-2">
                        <div className="flex items-center space-x-2">
                          <span className="text-sm text-gray-600">Qty: {item.quantity}</span>
                        </div>
                        <span className="font-semibold">${(item.price * item.quantity).toFixed(2)}</span>
                      </div>
                    </div>

                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onRemoveItem(item.item_id)}
                      className="text-red-500 hover:text-red-700 hover:bg-red-50"
                    >
                      <X className="w-4 h-4" />
                    </Button>
                  </div>
                ))}
              </div>

              <div className="border-t pt-4 mt-4">
                <div className="flex justify-between items-center mb-4">
                  <span className="text-lg font-semibold">Total:</span>
                  <span className="text-2xl font-bold text-blue-600">${totalPrice.toFixed(2)}</span>
                </div>

                <Button
                  className="w-full bg-blue-600 hover:bg-blue-700 text-white py-3"
                  onClick={handleCheckout}
                  disabled={items.length === 0}
                >
                  Checkout ({totalItems} items)
                </Button>
              </div>
            </>
          )}
        </div>
      </SheetContent>
    </Sheet>
  )
}
