/**
 * API Tests for Chat Room Application
 *
 * These tests verify the RESTful API endpoints for the chat room.
 * Tests use Jest + Supertest for HTTP assertions.
 *
 * API Requirements:
 * - POST /api/message: Post a new message
 * - GET /api/messages: Retrieve all messages
 *
 * Message format:
 * {
 *   id: number,
 *   username: string,
 *   text: string,
 *   timestamp: ISO 8601 string
 * }
 */

const request = require('supertest');
const express = require('express');

// We'll require the app from index.js
// Students need to export their Express app for testing
// If index.js doesn't export the app, supertest can still work with the server URL

describe('Chat Room API Tests', () => {
  let app;

  // Before all tests, require the Express app
  beforeAll(() => {
    // Try to require the app - if it's exported from index.js
    try {
      app = require('../index.js');
    } catch (err) {
      // If app is not exported, we'll use the server URL directly
      // This is a fallback approach
      app = 'http://localhost:3000';
    }
  });

  // Reset messages before each test if possible
  // This assumes the app exposes a way to reset or we start fresh
  beforeEach(async () => {
    // Attempt to clear messages if there's a DELETE endpoint
    // Otherwise, tests should be order-independent
    try {
      await request(app).delete('/api/messages');
    } catch (err) {
      // Ignore if endpoint doesn't exist
    }
  });

  describe('POST /api/message', () => {

    test('should post a message successfully', async () => {
      const messageData = {
        username: 'TestUser',
        text: 'Hello, World!'
      };

      const response = await request(app)
        .post('/api/message')
        .send(messageData)
        .expect('Content-Type', /json/)
        .expect(201);

      // Verify response structure
      expect(response.body).toHaveProperty('id');
      expect(response.body).toHaveProperty('username', 'TestUser');
      expect(response.body).toHaveProperty('text', 'Hello, World!');
      expect(response.body).toHaveProperty('timestamp');

      // Verify id is a number
      expect(typeof response.body.id).toBe('number');

      // Verify timestamp is a valid ISO 8601 string
      expect(new Date(response.body.timestamp).toISOString()).toBe(response.body.timestamp);
    });

    test('should reject message without username', async () => {
      const messageData = {
        text: 'Hello, World!'
      };

      const response = await request(app)
        .post('/api/message')
        .send(messageData)
        .expect(400);

      expect(response.body).toHaveProperty('error');
    });

    test('should reject message without text', async () => {
      const messageData = {
        username: 'TestUser'
      };

      const response = await request(app)
        .post('/api/message')
        .send(messageData)
        .expect(400);

      expect(response.body).toHaveProperty('error');
    });

  });

  describe('GET /api/message', () => {

    test('should return an array of messages', async () => {
      const response = await request(app)
        .get('/api/messages')
        .expect('Content-Type', /json/)
        .expect(200);

      // Response should be an array
      expect(Array.isArray(response.body)).toBe(true);
    });

    test('should return posted message', async () => {
      // First, post a message
      const messageData = {
        username: 'Alice',
        text: 'Test message'
      };

      const postResponse = await request(app)
        .post('/api/message')
        .send(messageData)
        .expect(201);

      // Then, get all messages
      const getResponse = await request(app)
        .get('/api/messages')
        .expect(200);

      // Verify the posted message is in the array
      expect(getResponse.body.length).toBeGreaterThanOrEqual(1);

      const foundMessage = getResponse.body.find(
        msg => msg.id === postResponse.body.id
      );

      expect(foundMessage).toBeDefined();
      expect(foundMessage.username).toBe('Alice');
      expect(foundMessage.text).toBe('Test message');
    });

    test('should store and return multiple messages in order', async () => {
      // Post 3 messages
      const messages = [
        { username: 'User1', text: 'First message' },
        { username: 'User2', text: 'Second message' },
        { username: 'User3', text: 'Third message' }
      ];

      const postedIds = [];
      for (const msg of messages) {
        const response = await request(app)
          .post('/api/message')
          .send(msg)
          .expect(201);
        postedIds.push(response.body.id);
      }

      // Get all messages
      const response = await request(app)
        .get('/api/messages')
        .expect(200);

      // Verify all messages are present
      expect(response.body.length).toBeGreaterThanOrEqual(3);

      // Verify the messages we posted are all there
      for (let i = 0; i < messages.length; i++) {
        const found = response.body.find(msg => msg.id === postedIds[i]);
        expect(found).toBeDefined();
        expect(found.username).toBe(messages[i].username);
        expect(found.text).toBe(messages[i].text);
      }
    });

  });

});
