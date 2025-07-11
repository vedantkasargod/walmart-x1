import { create } from "zustand"

export interface CartItem {
  item_id: string
  product_id: string
  name: string
  price: number
  quantity: number
  image_url?: string
}

interface CartStore {
  items: CartItem[]
  totalPrice: number
  setCart: (items: CartItem[]) => void
  addItems: (newItems: CartItem[]) => void
  removeItem: (itemId: string) => void
  clearCart: () => void
}

export const useCartStore = create<CartStore>((set, get) => ({
  items: [],
  totalPrice: 0,

  setCart: (items: CartItem[]) => {
    const totalPrice = items.reduce((sum, item) => sum + item.price * item.quantity, 0)
    set({ items, totalPrice })
  },

  addItems: (newItems: CartItem[]) => {
    const currentItems = get().items
    const updatedItems = [...currentItems]

    newItems.forEach((newItem) => {
      const existingItemIndex = updatedItems.findIndex((item) => item.product_id === newItem.product_id)

      if (existingItemIndex >= 0) {
        // Update quantity if item already exists
        updatedItems[existingItemIndex].quantity += newItem.quantity
      } else {
        // Add new item
        updatedItems.push(newItem)
      }
    })

    const totalPrice = updatedItems.reduce((sum, item) => sum + item.price * item.quantity, 0)
    set({ items: updatedItems, totalPrice })
  },

  removeItem: (itemId: string) => {
    const currentItems = get().items
    const updatedItems = currentItems.filter((item) => item.item_id !== itemId)
    const totalPrice = updatedItems.reduce((sum, item) => sum + item.price * item.quantity, 0)
    set({ items: updatedItems, totalPrice })
  },

  clearCart: () => {
    set({ items: [], totalPrice: 0 })
  },
}))
