import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

const ws = new WebSocket("ws://localhost:8000/ws");

ws.onopen = () => ws.send("Hello from WebSocket!");
ws.onmessage = (evt) => console.log(evt.data);

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
