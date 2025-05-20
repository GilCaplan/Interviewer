import React from 'react';

function Header({ title, subtitle }) {
  return (
    <div className="header">
      <h1>{title}</h1>
      <p>{subtitle}</p>
    </div>
  );
}

export default Header;