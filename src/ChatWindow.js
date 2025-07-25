import React, { useState, useEffect, useRef } from 'react';
import botLogo from './images/bot.png';
import userLogo from './images/user.png';
import headerLogo from './images/MM logo.png'; // New header logo (replace with your file)

export default function ChatWindow() {
  const [messages, setMessages] = useState([
    { sender: 'bot', text: 'You’re chatting with Voxi, your virtual assistant.', timestamp: new Date() }
  ]);
  const [input, setInput] = useState('');
  const [isMinimized, setIsMinimized] = useState(false);
  const [carouselIndexes, setCarouselIndexes] = useState({}); // Track carousel index per message
  const bottomRef = useRef(null);

  useEffect(() => {
    if (!isMinimized) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isMinimized]);

  const sendMessage = async () => {
    if (!input.trim()) return;
    const userMsg = { sender: 'user', text: input, timestamp: new Date() };
    setMessages((msgs) => [...msgs, userMsg]);
    setInput('');

    try {
      const res = await fetch('http://localhost:5005/webhooks/rest/webhook', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sender: 'user', message: input }),
      });
      const data = await res.json();
      data.forEach((botReply) => {
        setMessages((msgs) => [
          ...msgs,
          {
            sender: 'bot',
            text: botReply.text,
            attachment: botReply.attachment,
            timestamp: new Date()
          }
        ]);
      });
    } catch (err) {
      console.error('Error connecting to Rasa:', err);
      setMessages((msgs) => [...msgs, { sender: 'bot', text: 'Sorry, connection error!', timestamp: new Date() }]);
    }
  };

  const handleKey = (e) => {
    if (e.key === 'Enter') sendMessage();
  };

  const formatTimestamp = (date) => {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  // Carousel rendering for single-card with arrows
  function renderCarousel(attachment, msgIdx) {
    const packages = attachment.packages;
    const currentIdx = carouselIndexes[msgIdx] || 0;
    const pkg = packages[currentIdx];
    const atFirst = currentIdx === 0;
    const atLast = currentIdx === packages.length - 1;

    const handleArrow = (dir) => {
      setCarouselIndexes((prev) => ({
        ...prev,
        [msgIdx]: Math.max(0, Math.min(packages.length - 1, (prev[msgIdx] || 0) + dir))
      }));
    };

    return (
      <div className="carousel single-card">
        <button
          className="carousel-arrow"
          onClick={() => handleArrow(-1)}
          disabled={atFirst}
        >
          &#8592;
        </button>
        <div className="carousel-card">
          <h4>{pkg.title}</h4>
          <p>{pkg.details}</p>
          <button onClick={() => setInput(pkg.id)}>Choose {pkg.id}</button>
        </div>
        <button
          className="carousel-arrow"
          onClick={() => handleArrow(1)}
          disabled={atLast}
        >
          &#8594;
        </button>
        <div className="carousel-prompt">{attachment.prompt}</div>
      </div>
    );
  }

  return (
    <div className={`chat-window ${isMinimized ? 'minimized' : ''}`}>
      <div className="chat-header">
        <img src={headerLogo} alt="Header Logo" className="chat-header-logo" />
        <h3>Support Chatbot</h3>
        <button className="minimize-button" onClick={() => setIsMinimized(!isMinimized)}>
          {isMinimized ? '+' : '−'}
        </button>
      </div>
      {!isMinimized && (
        <>
          <div className="messages">
            {messages.map((msg, i) => (
              <div key={i} className={`message-container ${msg.sender}`}>
                {msg.sender === 'bot' && (
                  <img
                    src={botLogo}
                    alt={`${msg.sender} logo`}
                    className="message-avatar"
                  />
                )}
                <div className="message-content">
                  {msg.attachment && msg.attachment.type === "carousel" ? (
                    renderCarousel(msg.attachment, i)
                  ) : (
                    <div className={`bubble ${msg.sender}`}>{msg.text}</div>
                  )}
                  <div className="message-meta">
                    {msg.sender === 'bot' ? 'Bot' : 'You'} • {formatTimestamp(msg.timestamp)}
                  </div>
                </div>
                {msg.sender === 'user' && (
                  <img
                    src={userLogo}
                    alt={`${msg.sender} logo`}
                    className="message-avatar user-avatar"
                  />
                )}
              </div>
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
            <button className="send-button" onClick={sendMessage}>
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <line x1="22" y1="2" x2="11" y2="13" />
                <polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
            </button>
          </div>
        </>
      )}
    </div>
  );
}