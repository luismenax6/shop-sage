import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Cart } from './chat.models';

const EMPTY_CART: Cart = { items: [], count: 0, total: 0 };

/** Holds the current cart and performs deterministic add actions (no LLM). */
@Injectable({ providedIn: 'root' })
export class CartService {
  private http = inject(HttpClient);
  cart = signal<Cart>(EMPTY_CART);

  constructor() {
    // load any existing cart on startup
    this.http.get<Cart>('/cart').subscribe({ next: (c) => this.cart.set(c) });
  }

  add(sku: string): void {
    this.http.post<Cart>('/cart/add', { sku }).subscribe({ next: (c) => this.cart.set(c) });
  }

  /** Update from a /chat response so the mini-cart stays in sync. */
  sync(cart: Cart): void {
    if (cart) this.cart.set(cart);
  }
}
