import { describe, it, expect } from 'vitest';
import {
  createDefaultConfig,
  createDefaultSubAgent,
  createDefaultMcpServer,
  isSystemPromptPreset,
  type AgentConfig,
  type AgentDefinition,
  type SystemPromptPreset,
} from '../types';

describe('types helper functions', () => {
  describe('createDefaultConfig', () => {
    it('should create a valid default config', () => {
      const config = createDefaultConfig();

      expect(config).toBeDefined();
      expect(config.id).toBe('');
      expect(config.name).toBe('');
      expect(config.version).toBe('1.0.0');
      expect(config.allowed_tools).toEqual([]);
      expect(config.system_prompt).toBe('');
      expect(config.permission_mode).toBe('acceptEdits');
      expect(config.max_turns).toBe(100);
    });

    it('should have valid resource limits', () => {
      const config = createDefaultConfig();

      expect(config.resource_limits).toBeDefined();
      expect(config.resource_limits?.cpu_quota).toBe(200000);
      expect(config.resource_limits?.memory_limit).toBe('4g');
      expect(config.resource_limits?.storage_limit).toBe('10g');
    });

    it('should have empty mcp_servers and env', () => {
      const config = createDefaultConfig();

      expect(config.mcp_servers).toEqual({});
      expect(config.env).toEqual({});
    });
  });

  describe('createDefaultSubAgent', () => {
    it('should create a valid default sub-agent', () => {
      const agent = createDefaultSubAgent();

      expect(agent).toBeDefined();
      expect(agent.description).toBe('');
      expect(agent.prompt).toBe('');
      expect(agent.tools).toEqual([]);
      expect(agent.model).toBe('sonnet');
    });

    it('should match AgentDefinition type', () => {
      const agent: AgentDefinition = createDefaultSubAgent();

      // Type check passes if this compiles
      expect(agent).toBeDefined();
    });
  });

  describe('createDefaultMcpServer', () => {
    it('should create a stdio server by default', () => {
      const server = createDefaultMcpServer();

      expect(server.type).toBe('stdio');
      if ('command' in server) {
        expect(server.command).toBe('');
        expect(server.args).toEqual([]);
      }
    });

    it('should create a stdio server with command and args', () => {
      const server = createDefaultMcpServer('stdio');

      expect(server.type).toBe('stdio');
      if ('command' in server) {
        expect(server.command).toBe('');
        expect(server.args).toEqual([]);
      } else {
        throw new Error('Expected stdio server to have command property');
      }
    });

    it('should create an SSE server with url', () => {
      const server = createDefaultMcpServer('sse');

      expect(server.type).toBe('sse');
      if ('url' in server) {
        expect(server.url).toBe('');
      } else {
        throw new Error('Expected SSE server to have url property');
      }
    });

    it('should create an HTTP server with url', () => {
      const server = createDefaultMcpServer('http');

      expect(server.type).toBe('http');
      if ('url' in server) {
        expect(server.url).toBe('');
      } else {
        throw new Error('Expected HTTP server to have url property');
      }
    });
  });

  describe('isSystemPromptPreset', () => {
    it('should return true for preset objects', () => {
      const preset: SystemPromptPreset = {
        type: 'preset',
        preset: 'claude_code',
        append: 'Additional instructions',
      };

      expect(isSystemPromptPreset(preset)).toBe(true);
    });

    it('should return false for string prompts', () => {
      const prompt = 'You are a helpful assistant';

      expect(isSystemPromptPreset(prompt)).toBe(false);
    });

    it('should return false for undefined', () => {
      expect(isSystemPromptPreset(undefined)).toBe(false);
    });

    it('should return false for null', () => {
      expect(isSystemPromptPreset(null as any)).toBe(false);
    });

    it('should return false for empty string', () => {
      expect(isSystemPromptPreset('' as any)).toBe(false);
    });

    it('should return false for objects without type property', () => {
      const invalidPreset = {
        preset: 'claude_code',
      } as any;

      expect(isSystemPromptPreset(invalidPreset)).toBe(false);
    });
  });
});
