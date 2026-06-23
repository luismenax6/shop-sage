# ShopSage frontend

Angular 21 (standalone components + signals) — the chat UI for the ShopSage
assistant. A single conversational view with:

- chat window with user/assistant bubbles and **markdown rendering**
- **in-chat product cards** (image, price, stock, Add button)
- a **live mini-cart** kept in sync from the backend
- **citation chips** under support answers (source document + section)

## Develop

The frontend talks to the Flask backend on `:5001`, so start that first
(see the root [README](../README.md)). Then:

```bash
npm install
npm start            # ng serve on http://localhost:4200
```

A dev proxy (`proxy.conf.json`, wired in `angular.json`) forwards `/chat`,
`/cart`, and `/health` to the backend, so there are no CORS issues in dev.

## Build

```bash
npm run build        # outputs to dist/frontend/browser/
```

Deployed as a static site to S3 + CloudFront (see [`infra/`](../infra)).

## Structure

```
src/app/
├── app.ts / app.html / app.scss   # the chat view
├── chat.service.ts                # POST /chat, keeps conversation history
├── cart.service.ts                # GET /cart, POST /cart/add
├── chat.models.ts                 # response/message types
└── markdown.pipe.ts               # renders assistant markdown (marked)
```
