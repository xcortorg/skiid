const express = require('express');
const path = require('path');
const { setupRoutes } = require('./routes');
const { port } = require('./config');

const app = express();

app.use(express.json());

// Setup all routes
setupRoutes(app);

// Serve static files
app.use('/fun/tweet', express.static(path.join(__dirname, '../uploads/fun/tweet')));

// 404 handler
app.use((req, res) => {
  res.status(404).json({ error: '404', message: 'Endpoint not found' });
});

app.listen(port, () => {
  console.log(`Server running on port ${port}`);
});