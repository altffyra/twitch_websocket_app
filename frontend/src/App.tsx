import { useEffect, useRef, useState } from 'react'
import './App.css'

interface ChannelStats {
  mistakes: number;
  misspelled_per_min: number;
}

type Stats = Record<string, ChannelStats>;

function App() {
  const [channelInput, setChannelInput] = useState('');
  const [stats, setStats] = useState<Stats>({});
  const ws = useRef<WebSocket | null>(null);

  useEffect(() => {
    ws.current = new WebSocket("ws://localhost:6789/ws");
    ws.current.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as Stats;
        setStats(data);
      } catch (e) {
        console.error("Parsing error:", e);
      }
    };
    return () => {
      ws.current?.close();
    };
  }, []);

  const addChannel = () => {
    const channel = channelInput.trim().toLowerCase();
    if (channel && ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({ add_channel: channel }));
      setChannelInput('');
    }
  };

  return (
    <div style={{ padding: '20px' }}>
      <h1>Twitch Chat Spell Checker</h1>
      <div>
        <input
          type="text"
          placeholder="Enter Twitch channel"
          value={channelInput}
          onChange={(e) => setChannelInput(e.target.value)}
        />
        <button onClick={addChannel}>Add Channel</button>
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', marginTop: '20px' }}>
        {Object.entries(stats).map(([channel, data]) => (
          <div
            key={channel}
            style={{
              border: '1px solid #ccc',
              padding: '10px',
              margin: '10px',
              minWidth: '150px',
              borderRadius: '5px',
            }}
          >
            <strong>#{channel}</strong>
            <p>Mistakes: {data.mistakes}</p>
            <p>Misspelled/min: {data.misspelled_per_min}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

export default App;
