import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ChatResponse } from './chat.models';

/**
 * Talks to the Flask backend's /chat endpoint and keeps the conversation
 * history so multi-turn exchanges (e.g. confirm-before-write) work.
 */
@Injectable({ providedIn: 'root' })
export class ChatService {
  private http = inject(HttpClient);
  private history: unknown[] = [];

  send(message: string, confirm = false): Observable<ChatResponse> {
    return this.http.post<ChatResponse>('/chat', { message, confirm, history: this.history });
  }

  rememberHistory(history: unknown[]): void {
    this.history = history;
  }

  reset(): void {
    this.history = [];
  }
}
