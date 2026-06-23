import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ChatService } from './chat.service';
import { CartService } from './cart.service';
import { ChatMessage } from './chat.models';
import { MarkdownPipe } from './markdown.pipe';

@Component({
  selector: 'app-root',
  imports: [FormsModule, MarkdownPipe],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App {
  private chat = inject(ChatService);
  cartService = inject(CartService);

  messages = signal<ChatMessage[]>([]);
  loading = signal(false);
  draft = '';

  send(): void {
    const text = this.draft.trim();
    if (!text || this.loading()) return;

    this.messages.update((m) => [...m, { role: 'user', text }]);
    this.draft = '';
    this.loading.set(true);

    this.chat.send(text).subscribe({
      next: (res) => {
        this.chat.rememberHistory(res.history);
        this.cartService.sync(res.cart);
        this.messages.update((m) => [
          ...m,
          { role: 'assistant', text: res.answer, citations: res.citations, products: res.products },
        ]);
        this.loading.set(false);
      },
      error: () => {
        this.messages.update((m) => [
          ...m,
          { role: 'assistant', text: '⚠️ Sorry, I could not reach the assistant.' },
        ]);
        this.loading.set(false);
      },
    });
  }

  addToCart(sku: string): void {
    this.cartService.add(sku);
  }
}
