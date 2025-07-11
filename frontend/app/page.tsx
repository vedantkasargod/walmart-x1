"use client"

import type React from "react"

import { useState, useEffect, useRef } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent } from "@/components/ui/card"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import {
  Search,
  User,
  MapPin,
  ChevronDown,
  Sparkles,
  Mic,
  Upload,
  X,
  Loader2,
  AlertCircle,
  CreditCard,
  Wallet,
  Check,
  ShoppingCart,
  Wand2,
  Volume2,
} from "lucide-react"
import Image from "next/image"
import { useSpeech } from "@/hooks/useSpeech"
import { useCartStore } from "@/hooks/useCartStore"
import { CartSidebar } from "@/components/cart-sidebar"
import { QuantityControl } from "@/components/quantity-control"
import { toast } from "sonner"

// Type definitions for AI modes
type AIMode = "add_to_cart" | "build_cart" | "recommend"

// Type definitions for API responses
interface AddedItem {
  item_id: string
  product_id: string
  name: string
  price: number
  quantity: number
  image_url?: string
}

interface SmartSearchResponse {
  added_items: AddedItem[]
  message: string
}

// The corrected version
interface ExtractedItem {
  id?: number // <-- The crucial addition to fix the error
  product_name?: string
  name?: string
  quantity: number
  estimated_price?: number // It's also a good idea to add these other fields that come from your database search
  description?: string
  price?: number
  image_url?: string
  source?: string
}

interface BulkAddRequest {
  user_id: string
  products: ExtractedItem[]
}

interface BulkAddResponse {
  added_items: AddedItem[]
  message: string
}

interface CheckoutResponse {
  order_id: string
  message: string
  total_amount: number
}

// Updated API request interface to include ai_mode
interface ProcessQueryRequest {
  query: string
  user_id: string
  session_id: string
  ai_mode?: AIMode
}

export default function WalmartHomepage() {
  const [smartSearchQuery, setSmartSearchQuery] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [apiError, setApiError] = useState<string | null>(null)

  // AI Mode state
  const [aiMode, setAiMode] = useState<AIMode>("add_to_cart")

  // PDF Upload and AI processing states (renamed for clarity)
  const [isAILoading, setIsAILoading] = useState<boolean>(false)
  const [extractedList, setExtractedList] = useState<ExtractedItem[]>([])
  const [listError, setListError] = useState<string | null>(null)
  const [showReviewModal, setShowReviewModal] = useState(false)
  const [isAddingToCart, setIsAddingToCart] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Payment states
  const [isPaymentModalOpen, setIsPaymentModalOpen] = useState(false)
  const [paymentStatus, setPaymentStatus] = useState<"idle" | "processing" | "success">("idle")

  // Cart store
  const { items, totalPrice, setCart, addItems, removeItem, clearCart } = useCartStore()

  // Speech hook (upgraded with TTS)
  const {
    isListening,
    transcript,
    hasRecognitionSupport,
    isSpeaking,
    startListening,
    stopListening,
    speak,
    stopSpeaking,
  } = useSpeech()

  // Helper function to get AI mode label
  const getAIModeLabel = (mode: AIMode): string => {
    switch (mode) {
      case "add_to_cart":
        return "Add to Cart"
      case "build_cart":
        return "Build My Cart"
      case "recommend":
        return "Recommend"
      default:
        return "Add to Cart"
    }
  }

  // Helper function to get AI mode icon
  const getAIModeIcon = (mode: AIMode) => {
    switch (mode) {
      case "add_to_cart":
        return <ShoppingCart className="w-4 h-4" />
      case "build_cart":
        return <Wand2 className="w-4 h-4" />
      case "recommend":
        return <Sparkles className="w-4 h-4" />
      default:
        return <ShoppingCart className="w-4 h-4" />
    }
  }

  // Helper function to get dynamic placeholder text
  const getPlaceholderText = (mode: AIMode): string => {
    switch (mode) {
      case "add_to_cart":
        return "e.g., 2 boxes of cereal and a gallon of milk"
      case "build_cart":
        return "e.g., I'm hosting a birthday party for 10 people on a $50 budget"
      case "recommend":
        return "e.g., a good moisturizer for dry skin"
      default:
        return "e.g., 2 boxes of cereal and a gallon of milk"
    }
  }

  // Central conversational loop function
  const handleAIResponse = (message: string) => {
    if (!message.trim()) return

    speak(message, () => {
      // After speaking, automatically start listening for the next command
      setTimeout(() => {
        if (!isAILoading && !isLoading) {
          startListening()
        }
      }, 500) // Small delay to ensure clean transition
    })
  }

  // Update search query when transcript changes
  useEffect(() => {
    if (transcript) {
      setSmartSearchQuery(transcript)
    }
  }, [transcript])

  // Show review modal when extracted list is populated
  useEffect(() => {
    if (extractedList.length > 0) {
      setShowReviewModal(true)
      // Speak when review modal opens
      handleAIResponse(
        "I've created a list for your review. Please make any changes and click 'Add to Cart' when ready.",
      )
    }
  }, [extractedList])

  // Load existing cart on component mount
  useEffect(() => {
    const loadExistingCart = async () => {
      try {
        const userId = "user123" // This will be dynamic later
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/temp_cart/${userId}`)

        if (response.ok) {
          const cartData = await response.json()
          if (cartData.items) {
            setCart(cartData.items)
          }
        }
      } catch (error) {
        console.error("Failed to load existing cart:", error)
      }
    }

    loadExistingCart()
  }, [setCart])

  const handleMicrophoneClick = () => {
    if (isSpeaking) {
      stopSpeaking()
    } else if (isListening) {
      stopListening()
    } else {
      startListening()
    }
  }

  const handleUndo = async (itemId: string) => {
    // Optimistic update - remove from store immediately
    removeItem(itemId)

    try {
      const userId = "user123" // This will be dynamic later
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/temp_cart_item/${userId}/${itemId}`, {
        method: "DELETE",
      })

      if (!response.ok) {
        throw new Error("Failed to remove item from server")
      }

      toast.success("Item removed from cart")
    } catch (error) {
      console.error("Failed to remove item from server:", error)
      toast.error("Failed to remove item. Please try again.")
    }
  }

  const showItemAddedToast = (item: AddedItem) => {
    toast.success(`Added: ${item.name}`, {
      description: `Quantity: ${item.quantity} • $${(item.price * item.quantity).toFixed(2)}`,
      duration: 4000,
      action: {
        label: "Undo",
        onClick: () => handleUndo(item.item_id),
      },
    })
  }

  const handleSmartSearch = async () => {
    if (!smartSearchQuery.trim()) return

    // Use a more generic loading state, as discussed
    setIsAILoading(true) // Assuming you renamed setIsLoading to setIsAILoading
    setApiError(null)

    try {
      const requestBody: ProcessQueryRequest = {
        query: smartSearchQuery,
        user_id: "user123",
        session_id: "session456",
        ai_mode: aiMode,
      }

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/process_query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestBody),
      })

      const data = await response.json()

      if (!response.ok) {
        // Use the 'detail' key from FastAPI's HTTPException for the error message
        throw new Error(data.detail || "An unknown API error occurred.")
      }

      // --- START OF FIX ---
      if (aiMode === "build_cart") {
        // The backend now returns an object. We need to look inside `data.review_items`.
        if (data.review_items && Array.isArray(data.review_items) && data.review_items.length > 0) {
          // The normalization function is still a good idea.
          console.log("Raw review items from API:", data.review_items)
          const normalizedItems = data.review_items
          setExtractedList(normalizedItems)
          setSmartSearchQuery("")

          toast.success("Cart built successfully!", {
            description: `Found ${data.review_items.length} items for your review.`,
            duration: 3000,
          })

          // Speak the AI response
          if (data.message) {
            handleAIResponse(data.message)
          } else {
            handleAIResponse(`I've built a cart with ${data.review_items.length} items for your review.`)
          }
        } else {
          // This block now correctly handles the case where the AI found no relevant items.
          const noItemsMessage =
            data.message || "I couldn't find any items matching your request. Try being more specific."
          toast.info("No items found", {
            description: "Try refining your request or being more specific.",
            duration: 3000,
          })
          handleAIResponse(noItemsMessage)
        }
        // --- END OF FIX ---
      } else if (aiMode === "add_to_cart") {
        // This part is already correct and assumes `data` is the ProcessResponse object.
        const smartSearchData = data as SmartSearchResponse

        if (smartSearchData.added_items && smartSearchData.added_items.length > 0) {
          addItems(smartSearchData.added_items)

          smartSearchData.added_items.forEach((item) => {
            showItemAddedToast(item)
          })

          setSmartSearchQuery("")

          // Show summary toast
          const totalItems = smartSearchData.added_items.reduce((sum, item) => sum + item.quantity, 0)
          const totalValue = smartSearchData.added_items.reduce((sum, item) => sum + item.price * item.quantity, 0)

          setTimeout(() => {
            toast.info(`Smart Search Complete!`, {
              description: `Added ${totalItems} items worth $${totalValue.toFixed(2)} to your cart`,
              duration: 3000,
            })
          }, 500)

          // Speak the AI response
          if (smartSearchData.message) {
            handleAIResponse(smartSearchData.message)
          } else {
            handleAIResponse(`I've added ${totalItems} items to your cart for $${totalValue.toFixed(2)}.`)
          }
        } else {
          const noItemsMessage =
            smartSearchData.message || "I couldn't find any items matching your search. Try refining your query."
          toast.info("No items found", {
            description: "Try refining your search query",
            duration: 3000,
          })
          handleAIResponse(noItemsMessage)
        }
      } else if (aiMode === "recommend") {
        const recommendMessage = data.message || "Recommendation functionality is coming soon!"
        toast.info("Recommend mode", {
          description: "Recommendation functionality coming soon!",
          duration: 3000,
        })
        handleAIResponse(recommendMessage)
      }
    } catch (error: any) {
      console.error("Failed to fetch search results:", error)
      const errorMessage = error.message
      setApiError(errorMessage)
      toast.error("Search failed", {
        description: errorMessage,
        duration: 4000,
      })

      // Speak the error message
      handleAIResponse(`Sorry, there was an error: ${errorMessage}`)
    } finally {
      setIsAILoading(false) // Reset the generic loading state
    }
  }

  const handleUploadClick = () => {
    fileInputRef.current?.click()
  }

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    // Reset states
    setListError(null)
    setExtractedList([])
    setIsAILoading(true)

    try {
      const formData = new FormData()
      formData.append("file", file)

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/extract_from_list`, {
        method: "POST",
        body: formData,
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.message || "Failed to extract items from PDF")
      }

      if (Array.isArray(data) && data.length > 0) {
        setExtractedList(data)
        toast.success("PDF processed successfully!", {
          description: `Found ${data.length} items in your shopping list`,
          duration: 3000,
        })

        // Speak success message for PDF upload
        handleAIResponse(`I've successfully processed your PDF and found ${data.length} items in your shopping list.`)
      } else {
        const noItemsMessage =
          "I couldn't find any recognizable shopping items in your PDF. Please try a different file."
        toast.info("No items found", {
          description: "The PDF might not contain recognizable shopping items",
          duration: 4000,
        })
        handleAIResponse(noItemsMessage)
      }
    } catch (error: any) {
      console.error("Failed to process PDF:", error)
      const errorMessage = error.message || "Failed to process the PDF file. Please try again."
      setListError(errorMessage)
      toast.error("PDF processing failed", {
        description: errorMessage,
        duration: 4000,
      })

      // Speak error message for PDF upload
      handleAIResponse(`Sorry, I couldn't process your PDF file: ${errorMessage}`)
    } finally {
      setIsAILoading(false)
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = ""
      }
    }
  }

  const handleQuantityChange = (index: number, newQuantity: number) => {
    const updatedList = [...extractedList]
    updatedList[index].quantity = newQuantity
    setExtractedList(updatedList)
  }

  const handleRemoveItem = (index: number) => {
    const updatedList = extractedList.filter((_, i) => i !== index)
    setExtractedList(updatedList)
  }

  const handleConfirmAndAdd = async () => {
    if (extractedList.length === 0) {
      toast.error("No items to add", {
        description: "Please add some items to your list first",
      })
      return
    }

    setIsAddingToCart(true)

    try {
      // --- START OF ROBUST FIX ---
      const productsForBackend = extractedList.map((item) => {
        // This handles both potential naming conventions ('name' or 'product_name')
        const productName = item.name || item.product_name || "Unknown Item"

        // This ensures quantity is always a number, defaulting to 1.
        const productQuantity = typeof item.quantity === "number" ? item.quantity : 1

        return {
          id: item.id,
          name: productName,
          quantity: productQuantity,
          preferences: [], // Preferences are not relevant for this flow
        }
      })

      const bulkAddRequest: BulkAddRequest = {
        user_id: "user123", // This will be dynamic later
        products: productsForBackend,
      }

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/add_bulk_items`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(bulkAddRequest),
      })

      const data: BulkAddResponse = await response.json()
      console.log("Response from /add_bulk_items", data)

      if (!response.ok) {
        throw new Error(data.message || data.message || "Failed to add items to cart")
      }

      // Add items to cart store
      if (data && data.added_items && Array.isArray(data.added_items) && data.added_items.length > 0) {
        addItems(data.added_items)

        // Show toast for each added item
        data.added_items.forEach((item) => {
          showItemAddedToast(item)
        })

        // Show summary toast
        const totalItems = data.added_items.reduce((sum, item) => sum + item.quantity, 0)
        const totalValue = data.added_items.reduce((sum, item) => sum + item.price * item.quantity, 0)

        setTimeout(() => {
          toast.success(`Items Added to Cart!`, {
            description: `Added ${totalItems} items worth $${totalValue.toFixed(2)} to your cart`,
            duration: 3000,
          })
        }, 500)

        // Close modal and clear state
        setShowReviewModal(false)
        setExtractedList([])

        // Speak confirmation message
        if (data.message) {
          handleAIResponse(data.message)
        } else {
          handleAIResponse(`Perfect! I've added ${totalItems} items worth $${totalValue.toFixed(2)} to your cart.`)
        }
      } else {
        console.warn("API call was successful, but no items were added.")
        toast.info("No new items were added to the cart.")
        setShowReviewModal(false)
        setExtractedList([])
        handleAIResponse("No new items were added to your cart.")
      }
    } catch (error: any) {
      console.error("Failed to add bulk items:", error)
      const errorMessage = error.message || "Please try again later"
      toast.error("Failed to add items", {
        description: errorMessage,
        duration: 4000,
      })
      handleAIResponse(`Sorry, I couldn't add the items to your cart: ${errorMessage}`)
    } finally {
      setIsAddingToCart(false)
    }
  }

  const handleCancelReview = () => {
    setShowReviewModal(false)
    setExtractedList([])
    setListError(null)
    handleAIResponse("Okay, I've cancelled the review. What would you like to do next?")
  }

  const handleCheckout = () => {
    setIsPaymentModalOpen(true)
    setPaymentStatus("idle")
  }

  const handleFinalizePayment = async () => {
    setPaymentStatus("processing")

    // Simulate payment delay
    setTimeout(async () => {
      try {
        const userId = "user123" // This will be dynamic later
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/checkout/${userId}`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            items: items,
            total_amount: totalPrice,
          }),
        })

        const data: CheckoutResponse = await response.json()

        if (!response.ok) {
          throw new Error(data.message || "Checkout failed")
        }

        // Success
        setPaymentStatus("success")
        clearCart()

        toast.success("Order Placed! Your items are on their way.", {
          description: `Order ID: ${data.order_id}`,
          duration: 5000,
        })

        // Speak success message
        handleAIResponse(
          `Excellent! Your order has been placed successfully. Your order ID is ${data.order_id}. Your items are on their way!`,
        )

        // Close modal after showing success message
        setTimeout(() => {
          setIsPaymentModalOpen(false)
          setPaymentStatus("idle")
        }, 2000)
      } catch (error: any) {
        console.error("Checkout failed:", error)
        setPaymentStatus("idle")
        const errorMessage = error.message || "Please try again later"
        toast.error("Checkout failed", {
          description: errorMessage,
          duration: 4000,
        })
        handleAIResponse(`Sorry, there was an issue with your checkout: ${errorMessage}`)
      }
    }, 2000)
  }

  const totalCartItems = items.reduce((sum, item) => sum + item.quantity, 0)

  // Determine the modal title based on the source of the extracted list
  const getModalTitle = () => {
    if (aiMode === "build_cart" && extractedList.length > 0) {
      return "Review Your AI-Built Cart"
    }
    return "Review Your Shopping List"
  }

  return (
    <div className="min-h-screen bg-white">
      {/* Hidden file input */}
      <input ref={fileInputRef} type="file" accept=".pdf" onChange={handleFileUpload} className="hidden" />

      {/* Header */}
      <header className="bg-blue-600 text-white">
        <div className="container mx-auto px-4">
          {/* Top Header */}
          <div className="flex items-center justify-between py-3">
            {/* Logo and Location */}
            <div className="flex items-center space-x-4">
              <div className="text-2xl font-bold">
                <span className="bg-yellow-400 text-blue-600 px-2 py-1 rounded">W</span>
                <span className="ml-1">almart</span>
              </div>
              <div className="flex items-center space-x-1 text-sm">
                <MapPin className="w-4 h-4" />
                <span>Pickup or delivery?</span>
                <span className="font-semibold">Sacramento, 95829</span>
                <ChevronDown className="w-4 h-4" />
              </div>
            </div>

            {/* Search Bar */}
            <div className="flex-1 max-w-2xl mx-8">
              <div className="relative">
                <Input
                  placeholder="Search everything at Walmart online and in store"
                  className="w-full pl-4 pr-12 py-3 rounded-full text-black"
                />
                <Button
                  size="icon"
                  className="absolute right-1 top-1 rounded-full bg-yellow-400 hover:bg-yellow-500 text-black"
                >
                  <Search className="w-5 h-5" />
                </Button>
              </div>
            </div>

            {/* Right Side */}
            <div className="flex items-center space-x-6">
              <div className="text-center">
                <div className="text-sm">Reorder</div>
                <div className="font-semibold">My Items</div>
              </div>
              <div className="text-center">
                <User className="w-6 h-6 mx-auto" />
                <div className="text-sm">Sign In</div>
                <div className="font-semibold">Account</div>
              </div>

              {/* Smart Cart */}
              <div className="text-center">
                <CartSidebar onRemoveItem={handleUndo} onCheckout={handleCheckout} />
                <div className="text-sm mt-1">${totalPrice.toFixed(2)}</div>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Navigation */}
      <nav className="bg-white border-b">
        <div className="container mx-auto px-4">
          <div className="flex items-center space-x-8 py-3">
            <Button variant="ghost" className="flex items-center space-x-1">
              <div className="grid grid-cols-3 gap-1 w-4 h-4">
                {[...Array(9)].map((_, i) => (
                  <div key={i} className="w-1 h-1 bg-gray-600 rounded-full" />
                ))}
              </div>
              <span>Departments</span>
              <ChevronDown className="w-4 h-4" />
            </Button>
            <Button variant="ghost" className="flex items-center space-x-1">
              <span>Services</span>
              <ChevronDown className="w-4 h-4" />
            </Button>
            <div className="flex space-x-6 text-sm">
              <a href="#" className="hover:underline">
                Get it Fast
              </a>
              <a href="#" className="hover:underline">
                New Arrivals
              </a>
              <a href="#" className="hover:underline">
                Rollbacks & more
              </a>
              <a href="#" className="hover:underline">
                Dinner Made Easy
              </a>
              <a href="#" className="hover:underline">
                Pharmacy Delivery
              </a>
              <a href="#" className="hover:underline">
                Trending
              </a>
              <a href="#" className="hover:underline">
                Swim Shop
              </a>
              <a href="#" className="hover:underline">
                My Items
              </a>
              <a href="#" className="hover:underline">
                Auto Service
              </a>
              <a href="#" className="hover:underline">
                Walmart+
              </a>
            </div>
            <Button variant="ghost" className="ml-auto">
              More <ChevronDown className="w-4 h-4 ml-1" />
            </Button>
          </div>
        </div>
      </nav>

      {/* Smart Search Bar */}
      <div className="bg-blue-50 border-b-2 border-blue-100">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center space-x-4 max-w-4xl mx-auto">
            <Sparkles className="w-6 h-6 text-blue-600" />

            {/* AI Mode Dropdown */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" className="flex items-center space-x-2 px-4 py-3 bg-white border-gray-300">
                  {getAIModeIcon(aiMode)}
                  <span className="font-medium">{getAIModeLabel(aiMode)}</span>
                  <ChevronDown className="w-4 h-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start" className="w-48">
                <DropdownMenuItem onClick={() => setAiMode("add_to_cart")} className="flex items-center space-x-3">
                  <ShoppingCart className="w-4 h-4" />
                  <span>Add to Cart</span>
                  {aiMode === "add_to_cart" && <Check className="w-4 h-4 ml-auto text-blue-600" />}
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setAiMode("build_cart")} className="flex items-center space-x-3">
                  <Wand2 className="w-4 h-4" />
                  <span>Build My Cart</span>
                  {aiMode === "build_cart" && <Check className="w-4 h-4 ml-auto text-blue-600" />}
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setAiMode("recommend")} className="flex items-center space-x-3">
                  <Sparkles className="w-4 h-4" />
                  <span>Recommend</span>
                  {aiMode === "recommend" && <Check className="w-4 h-4 ml-auto text-blue-600" />}
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>

            <div className="flex-1">
              <Input
                placeholder={`Try our Smart Search: ${getPlaceholderText(aiMode)}`}
                value={smartSearchQuery}
                onChange={(e) => setSmartSearchQuery(e.target.value)}
                className="w-full py-3 text-lg"
                onKeyPress={(e) => e.key === "Enter" && handleSmartSearch()}
                disabled={isLoading || isAILoading}
              />
            </div>

            {/* Enhanced Microphone Button with Speaking Indicator */}
            {hasRecognitionSupport && (
              <Button
                variant={isListening || isSpeaking ? "default" : "outline"}
                size="icon"
                onClick={handleMicrophoneClick}
                className={`p-3 ${
                  isListening
                    ? "bg-red-600 hover:bg-red-700 text-white animate-pulse"
                    : isSpeaking
                      ? "bg-green-600 hover:bg-green-700 text-white animate-pulse"
                      : "border-gray-300 hover:border-gray-400"
                }`}
                title={
                  isSpeaking
                    ? "AI is speaking - click to stop"
                    : isListening
                      ? "Listening - click to stop"
                      : "Start voice input"
                }
                disabled={isLoading || isAILoading}
              >
                {isSpeaking ? <Volume2 className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
              </Button>
            )}

            {/* Upload List Button */}
            <Button
              variant="outline"
              onClick={handleUploadClick}
              disabled={isAILoading}
              className="px-6 py-3 text-lg border-blue-300 hover:border-blue-400 hover:bg-blue-50 bg-transparent"
            >
              {isAILoading ? (
                <>
                  <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <Upload className="w-5 h-5 mr-2" />
                  Upload List
                </>
              )}
            </Button>

            <Button
              onClick={handleSmartSearch}
              className="bg-blue-600 hover:bg-blue-700 px-8 py-3 text-lg"
              disabled={isLoading || isAILoading || !smartSearchQuery.trim()}
            >
              {isLoading || isAILoading ? "Searching..." : "Search"}
            </Button>
          </div>
        </div>
      </div>

      {/* Error Alert */}
      {listError && (
        <div className="container mx-auto px-4 py-2">
          <Alert variant="destructive" className="max-w-4xl mx-auto">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{listError}</AlertDescription>
          </Alert>
        </div>
      )}

      {/* Review Your List Modal */}
      <Dialog open={showReviewModal} onOpenChange={setShowReviewModal}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-hidden flex flex-col">
          <DialogHeader>
            <DialogTitle className="text-2xl font-bold">{getModalTitle()}</DialogTitle>
          </DialogHeader>

          <div className="flex-1 overflow-y-auto space-y-4 py-4">
            {extractedList.map((item, index) => (
              <div key={index} className="flex items-center justify-between p-4 border rounded-lg">
                <div className="flex-1 flex items-center gap-4">
                  {item.image_url && (
                    <Image
                      src={item.image_url || "/placeholder.svg"}
                      alt={item.name || "Product image"}
                      width={64}
                      height={64}
                      className="rounded object-cover"
                    />
                  )}
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="font-medium text-lg capitalize">{item.name}</h3>
                      {item.source === "Recommendation" && (
                        <span className="ml-2 px-2 py-0.5 text-xs bg-blue-100 text-blue-700 rounded-full font-semibold">
                          Recommendation
                        </span>
                      )}
                    </div>
                    {item.price !== undefined && <p className="text-sm text-gray-600">${item.price.toFixed(2)}</p>}
                    {item.description && <p className="text-xs text-gray-500 mt-1">{item.description}</p>}
                  </div>
                </div>

                <div className="flex items-center space-x-4">
                  <QuantityControl
                    quantity={item.quantity}
                    onQuantityChange={(newQuantity) => handleQuantityChange(index, newQuantity)}
                  />

                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleRemoveItem(index)}
                    className="text-red-500 hover:text-red-700 hover:bg-red-50"
                  >
                    <X className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            ))}

            {extractedList.length === 0 && (
              <div className="text-center py-8 text-gray-500">
                <p>No items in your list</p>
              </div>
            )}
          </div>

          <DialogFooter className="flex space-x-2">
            <Button variant="outline" onClick={handleCancelReview}>
              Cancel
            </Button>
            <Button
              onClick={handleConfirmAndAdd}
              className="bg-blue-600 hover:bg-blue-700"
              disabled={extractedList.length === 0 || isAddingToCart}
            >
              {isAddingToCart ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />
                  Adding...
                </>
              ) : (
                `Add to Cart (${extractedList.length} items)`
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Payment Modal */}
      <Dialog open={isPaymentModalOpen} onOpenChange={setIsPaymentModalOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="text-2xl font-bold text-center">Complete Your Order</DialogTitle>
          </DialogHeader>

          <div className="py-6">
            {paymentStatus === "idle" && (
              <div className="space-y-6">
                <div className="text-center">
                  <div className="text-lg font-semibold mb-2">Total Amount</div>
                  <div className="text-3xl font-bold text-blue-600">${totalPrice.toFixed(2)}</div>
                  <div className="text-sm text-gray-600 mt-1">{totalCartItems} items</div>
                </div>

                <div className="space-y-3">
                  <Button onClick={handleFinalizePayment} className="w-full bg-blue-600 hover:bg-blue-700 py-4 text-lg">
                    <CreditCard className="w-5 h-5 mr-3" />
                    Pay with Card
                  </Button>

                  <Button
                    onClick={handleFinalizePayment}
                    variant="outline"
                    className="w-full py-4 text-lg border-blue-300 hover:bg-blue-50 bg-transparent"
                  >
                    <Wallet className="w-5 h-5 mr-3" />
                    Pay with Digital Wallet
                  </Button>
                </div>
              </div>
            )}

            {paymentStatus === "processing" && (
              <div className="text-center py-8">
                <Loader2 className="w-12 h-12 animate-spin mx-auto mb-4 text-blue-600" />
                <div className="text-lg font-semibold">Processing Payment...</div>
                <div className="text-gray-600 mt-2">Please wait while we process your order</div>
              </div>
            )}

            {paymentStatus === "success" && (
              <div className="text-center py-8">
                <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <Check className="w-8 h-8 text-green-600" />
                </div>
                <div className="text-xl font-bold text-green-600 mb-2">Order Placed Successfully!</div>
                <div className="text-gray-600">Your items are on their way</div>
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Walmart+ Banner */}
      <div className="bg-yellow-400 text-black">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="text-2xl font-bold">Walmart+</div>
              <div className="text-lg">Get 50% off a year of Walmart+ to shop hot Deals first</div>
            </div>
            <div className="flex items-center space-x-4">
              <div className="text-center">
                <div className="text-sm">Early Access starts in</div>
                <div className="text-2xl font-bold">14 : 52</div>
                <div className="text-xs">hours mins</div>
              </div>
              <Button className="bg-white text-black hover:bg-gray-100">Join Walmart+</Button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {/* Classroom Supplies */}
          <Card className="bg-blue-400 text-white overflow-hidden">
            <CardContent className="p-6">
              <h2 className="text-2xl font-bold mb-2">Tons of classroom supplies for teachers</h2>
              <Button variant="secondary" className="mt-4">
                Shop now
              </Button>
              <div className="mt-4">
                <Image
                  src="/placeholder.svg?height=150&width=200"
                  alt="School supplies"
                  width={200}
                  height={150}
                  className="rounded"
                />
              </div>
            </CardContent>
          </Card>

          {/* School Supply Lists */}
          <Card className="bg-blue-300 text-white overflow-hidden lg:col-span-1">
            <CardContent className="p-6">
              <h2 className="text-3xl font-bold mb-2">Easily find all they need</h2>
              <h3 className="text-4xl font-bold mb-4">1-click school supply lists</h3>
              <Button variant="secondary">Find your list</Button>
              <div className="mt-4">
                <Image
                  src="/placeholder.svg?height=200&width=300"
                  alt="School supplies and mobile app"
                  width={300}
                  height={200}
                  className="rounded"
                />
              </div>
            </CardContent>
          </Card>

          {/* Beauty Section */}
          <div className="space-y-6">
            <Card className="bg-pink-100 overflow-hidden">
              <CardContent className="p-6">
                <h2 className="text-2xl font-bold text-black mb-2">Hot, new beauty from $10</h2>
                <Button variant="link" className="text-blue-600 p-0">
                  Shop now
                </Button>
                <div className="mt-4">
                  <Image
                    src="/placeholder.svg?height=120&width=200"
                    alt="Beauty products"
                    width={200}
                    height={120}
                    className="rounded"
                  />
                </div>
              </CardContent>
            </Card>

            <Card className="bg-pink-200 overflow-hidden">
              <CardContent className="p-6">
                <h2 className="text-2xl font-bold text-black mb-1">Premium beauty.</h2>
                <h3 className="text-2xl font-bold text-black mb-2">Victoria's Secret.</h3>
                <Button variant="link" className="text-blue-600 p-0">
                  Shop now
                </Button>
                <div className="mt-4">
                  <Image
                    src="/placeholder.svg?height=120&width=200"
                    alt="Victoria's Secret perfumes"
                    width={200}
                    height={120}
                    className="rounded"
                  />
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Hot New Arrivals */}
          <Card className="bg-green-700 text-white overflow-hidden">
            <CardContent className="p-6">
              <h2 className="text-2xl font-bold mb-2">Hot new arrivals</h2>
              <Button variant="secondary" className="mt-4">
                Shop now
              </Button>
              <div className="mt-4">
                <Image
                  src="/placeholder.svg?height=150&width=200"
                  alt="New arrival shoes"
                  width={200}
                  height={150}
                  className="rounded"
                />
              </div>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  )
}
