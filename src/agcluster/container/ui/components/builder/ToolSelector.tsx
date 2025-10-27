'use client';

const AVAILABLE_TOOLS = [
  { name: 'Bash', description: 'Execute shell commands', category: 'System' },
  { name: 'Read', description: 'Read file contents', category: 'Files' },
  { name: 'Write', description: 'Write or create files', category: 'Files' },
  { name: 'Edit', description: 'Edit existing files', category: 'Files' },
  { name: 'Grep', description: 'Search file contents', category: 'Search' },
  { name: 'Glob', description: 'Find files by pattern', category: 'Search' },
  { name: 'WebFetch', description: 'Fetch web pages', category: 'Web' },
  { name: 'WebSearch', description: 'Search the web', category: 'Web' },
  { name: 'Task', description: 'Delegate to sub-agents', category: 'Multi-Agent' },
  { name: 'TodoWrite', description: 'Track task progress', category: 'Planning' },
  { name: 'NotebookEdit', description: 'Edit Jupyter notebooks', category: 'Data' },
];

interface ToolSelectorProps {
  selected: string[];
  onChange: (tools: string[]) => void;
}

export function ToolSelector({ selected, onChange }: ToolSelectorProps) {
  const toggleTool = (toolName: string) => {
    if (selected.includes(toolName)) {
      onChange(selected.filter(t => t !== toolName));
    } else {
      onChange([...selected, toolName]);
    }
  };

  const selectAll = () => {
    onChange(AVAILABLE_TOOLS.map(t => t.name));
  };

  const clearAll = () => {
    onChange([]);
  };

  const categories = [...new Set(AVAILABLE_TOOLS.map(t => t.category))];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h4 className="font-medium text-sm">
          {selected.length} of {AVAILABLE_TOOLS.length} tools selected
        </h4>
        <div className="flex gap-2">
          <button
            onClick={selectAll}
            className="text-xs px-3 py-1 bg-gray-800 hover:bg-gray-700 rounded"
          >
            Select All
          </button>
          <button
            onClick={clearAll}
            className="text-xs px-3 py-1 bg-gray-800 hover:bg-gray-700 rounded"
          >
            Clear All
          </button>
        </div>
      </div>

      {categories.map(category => (
        <div key={category} className="bg-gray-900/50 rounded-lg p-4">
          <h4 className="text-sm font-semibold text-gray-300 mb-3">{category}</h4>
          <div className="grid grid-cols-2 gap-2">
            {AVAILABLE_TOOLS
              .filter(t => t.category === category)
              .map(tool => (
                <label
                  key={tool.name}
                  className="flex items-start gap-2 p-3 rounded border border-gray-800 cursor-pointer hover:bg-gray-800 transition-colors"
                >
                  <input
                    type="checkbox"
                    checked={selected.includes(tool.name)}
                    onChange={() => toggleTool(tool.name)}
                    className="mt-1 w-4 h-4"
                  />
                  <div className="flex-1">
                    <div className="text-sm font-medium">{tool.name}</div>
                    <div className="text-xs text-gray-500">{tool.description}</div>
                  </div>
                </label>
              ))}
          </div>
        </div>
      ))}
    </div>
  );
}
