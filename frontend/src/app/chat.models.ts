export interface Citation {
  source: string;
  section: string;
  similarity: number;
}

export interface ToolCall {
  name: string;
  status: string;
}

export interface Product {
  sku: string;
  name: string;
  category: string;
  price: number;
  stock: number;
  description: string;
  image_url: string;
}

export interface CartItem {
  sku: string;
  name: string;
  price: number;
  quantity: number;
  image_url: string;
}

export interface Cart {
  items: CartItem[];
  count: number;
  total: number;
}

/** Shape returned by the backend POST /chat */
export interface ChatResponse {
  answer: string;
  citations: Citation[];
  products: Product[];
  cart: Cart;
  tool_calls: ToolCall[];
  history: unknown[];
}

/** A message rendered in the chat window */
export interface ChatMessage {
  role: 'user' | 'assistant';
  text: string;
  citations?: Citation[];
  products?: Product[];
}
