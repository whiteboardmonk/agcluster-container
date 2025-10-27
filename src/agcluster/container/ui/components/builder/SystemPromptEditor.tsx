'use client';

import { SystemPrompt, SystemPromptPreset, isSystemPromptPreset } from './types';

interface SystemPromptEditorProps {
  value: SystemPrompt | undefined;
  onChange: (value: SystemPrompt) => void;
}

export function SystemPromptEditor({ value, onChange }: SystemPromptEditorProps) {
  const isPreset = isSystemPromptPreset(value);
  const promptType = isPreset ? 'preset' : 'custom';

  const handleTypeChange = (newType: 'custom' | 'preset') => {
    if (newType === 'preset') {
      // Switch to preset mode
      onChange({
        type: 'preset',
        preset: 'claude_code',
        append: '',
      });
    } else {
      // Switch to custom mode
      onChange('');
    }
  };

  const handleCustomChange = (text: string) => {
    onChange(text);
  };

  const handleAppendChange = (text: string) => {
    if (isPreset) {
      onChange({
        ...value,
        append: text,
      });
    }
  };

  return (
    <div className="space-y-3">
      <label className="block text-sm font-medium">System Prompt</label>

      {/* Type Selector */}
      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => handleTypeChange('preset')}
          className={`
            px-4 py-2 rounded text-sm font-medium transition-colors
            ${promptType === 'preset'
              ? 'bg-gray-700 text-white'
              : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
            }
          `}
        >
          Preset (Claude Code)
        </button>
        <button
          type="button"
          onClick={() => handleTypeChange('custom')}
          className={`
            px-4 py-2 rounded text-sm font-medium transition-colors
            ${promptType === 'custom'
              ? 'bg-gray-700 text-white'
              : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
            }
          `}
        >
          Custom
        </button>
      </div>

      {/* Preset Mode */}
      {isPreset && (
        <div className="space-y-3">
          <div className="p-3 bg-gray-900/40 border border-gray-700/50 rounded text-sm">
            <p className="text-gray-300 mb-1">
              <strong>Using Claude Code Preset</strong>
            </p>
            <p className="text-gray-400 text-xs">
              This preset includes optimized instructions for software development, TDD principles,
              and tool usage. You can add additional instructions below.
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium mb-2 text-gray-300">
              Additional Instructions (Optional)
            </label>
            <textarea
              value={value.append || ''}
              onChange={(e) => handleAppendChange(e.target.value)}
              placeholder="Add any additional instructions to append to the preset..."
              rows={5}
              className="w-full px-4 py-2 bg-gray-900 border border-gray-800 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm"
            />
            <p className="text-xs text-gray-500 mt-1">
              These instructions will be appended to the claude_code preset
            </p>
          </div>
        </div>
      )}

      {/* Custom Mode */}
      {!isPreset && (
        <div>
          <textarea
            value={typeof value === 'string' ? value : ''}
            onChange={(e) => handleCustomChange(e.target.value)}
            placeholder="You are a helpful assistant that specializes in..."
            rows={10}
            className="w-full px-4 py-2 bg-gray-900 border border-gray-800 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm"
          />
          <p className="text-xs text-gray-500 mt-1">
            Complete custom system prompt that defines the agent&apos;s behavior
          </p>
        </div>
      )}
    </div>
  );
}
