import React, { useState, useEffect, useRef } from 'react';

export default function ChatWindow() {
  const [messages, setMessages] = useState([
    { sender: 'bot', text: 'Hello! Welcome to the Billing Issues Chatbot. How can I assist you today?' }
  ]);
  const [input, setInput] = useState('');
  const bottomRef = useRef(null);

  // Scroll to bottom on new message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim()) return;
    const userMsg = { sender: 'user', text: input };
    setMessages((msgs) => [...msgs, userMsg]);
    setInput('');

    // Call Rasa REST webhook
    try {
      const res = await fetch('http://localhost:5005/webhooks/rest/webhook', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sender: 'user', message: input }),
      });
      const data = await res.json();
      // Append each bot reply
      data.forEach((botReply) => {
        setMessages((msgs) => [...msgs, { sender: 'bot', text: botReply.text }]);
      });
    } catch (err) {
      console.error('Error connecting to Rasa:', err);
      setMessages((msgs) => [...msgs, { sender: 'bot', text: 'Sorry, connection error!' }]);
    }
  };

  const handleKey = (e) => {
    if (e.key === 'Enter') sendMessage();
  };

  return (
    <div className="chat-window">
      <div className="messages">
        {messages.map((msg, i) => (
          <div key={i} className={`bubble ${msg.sender}`}>{msg.text}</div>
        ))}
        <div ref={bottomRef} />
      </div>
      <div className="input-area">
        <input
          type="text"
          placeholder="Type your billing issue..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKey}
        />
        <button onClick={sendMessage}>Send</button>
      </div>
    </div>
  );
}