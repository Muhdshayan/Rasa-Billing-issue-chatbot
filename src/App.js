import React from 'react';
import ChatWindow from './ChatWindow';
import bg1 from './bg2.jpg';

export default function App() {
  return (
    <div
      className="app-container"
      style={{
        backgroundImage: `url(${bg1})`,
        backgroundSize: 'cover',
        backgroundPosition: 'center',
        backgroundRepeat: 'no-repeat',
        minHeight: '100vh',
      }}
    >
      <h1 className="billing-heading">Billing Issues Chatbot</h1>
      <ChatWindow />
    </div>
  );
}