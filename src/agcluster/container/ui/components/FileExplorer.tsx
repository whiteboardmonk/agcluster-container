'use client';

import { useState, useEffect, useCallback } from 'react';
import { ChevronRight, ChevronDown, File, Folder, Download, RefreshCw, Upload } from 'lucide-react';
import { FileUploadModal } from './FileUploadModal';

interface FileNode {
  name: string;
  type: 'file' | 'directory';
  path: string;
  children?: FileNode[];
}

interface FileExplorerProps {
  sessionId: string;
  onFileSelect: (path: string) => void;
  selectedFile: string | null;
}

export function FileExplorer({ sessionId, onFileSelect, selectedFile }: FileExplorerProps) {
  const [tree, setTree] = useState<FileNode | null>(null);
  const [expanded, setExpanded] = useState<Set<string>>(new Set(['/']));
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showUploadModal, setShowUploadModal] = useState(false);

  const loadFiles = useCallback(async () => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const apiKey = localStorage.getItem('anthropic_api_key');

      if (!apiKey) {
        throw new Error('No API key found. Please launch an agent from the dashboard first.');
      }

      // Add timeout to fetch request
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000); // 5 second timeout

      const res = await fetch(`${apiUrl}/api/files/${sessionId}`, {
        headers: {
          'Authorization': `Bearer ${apiKey}`
        },
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!res.ok) {
        throw new Error(`Failed to load files: ${res.statusText}`);
      }

      const data = await res.json();
      setTree(data.tree);
      setError(null);
      setLoading(false);
    } catch (error) {
      console.error('Failed to load files:', error);
      // Only set error state if it's not an abort error (timeout)
      if (error instanceof Error && error.name === 'AbortError') {
        console.log('File loading timed out, will retry...');
      } else {
        setError(error instanceof Error ? error.message : 'Failed to load files');
      }
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    loadFiles();

    // Poll for file changes every 3 seconds
    const interval = setInterval(loadFiles, 3000);
    return () => clearInterval(interval);
  }, [loadFiles]);

  const toggleExpanded = (path: string) => {
    const newExpanded = new Set(expanded);
    if (newExpanded.has(path)) {
      newExpanded.delete(path);
    } else {
      newExpanded.add(path);
    }
    setExpanded(newExpanded);
  };

  const downloadWorkspace = async () => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const apiKey = localStorage.getItem('anthropic_api_key');

      if (!apiKey) {
        console.error('No API key found');
        return;
      }

      const response = await fetch(`${apiUrl}/api/files/${sessionId}/download`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${apiKey}`
        }
      });

      if (!response.ok) {
        console.error('Download failed:', response.statusText);
        return;
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `workspace_${sessionId.slice(0, 8)}.zip`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Failed to download workspace:', error);
    }
  };

  const renderNode = (node: FileNode, level: number = 0): React.ReactNode => {
    const isExpanded = expanded.has(node.path);
    const isDirectory = node.type === 'directory';
    const isSelected = selectedFile === node.path;

    return (
      <div key={node.path}>
        <div
          className={`flex items-center gap-1 px-2 py-1 hover:bg-gray-800 cursor-pointer rounded text-sm ${
            isSelected ? 'bg-gray-900/50' : ''
          }`}
          style={{ paddingLeft: `${level * 12 + 8}px` }}
          onClick={() => {
            if (isDirectory) {
              toggleExpanded(node.path);
            } else {
              onFileSelect(node.path);
            }
          }}
          data-testid={`file-node-${node.path}`}
        >
          {isDirectory && (
            isExpanded ? (
              <ChevronDown className="w-4 h-4 text-gray-400 flex-shrink-0" />
            ) : (
              <ChevronRight className="w-4 h-4 text-gray-400 flex-shrink-0" />
            )
          )}
          {!isDirectory && <div className="w-4" />}
          {isDirectory ? (
            <Folder className="w-4 h-4 text-gray-400 flex-shrink-0" />
          ) : (
            <File className="w-4 h-4 text-gray-400 flex-shrink-0" />
          )}
          <span className="flex-1 truncate" title={node.name}>{node.name}</span>
        </div>

        {isDirectory && isExpanded && node.children && node.children.length > 0 && (
          <div>
            {node.children.map(child => renderNode(child, level + 1))}
          </div>
        )}
      </div>
    );
  };

  if (loading) {
    return (
      <div className="flex flex-col h-full glass border-l border-gray-800">
        <div className="p-3 border-b border-gray-800">
          <h3 className="text-sm font-semibold">Workspace Files</h3>
        </div>
        <div className="flex-1 flex items-center justify-center">
          <div className="text-sm text-gray-500">Loading files...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col h-full glass border-l border-gray-800">
        <div className="p-3 border-b border-gray-800">
          <h3 className="text-sm font-semibold">Workspace Files</h3>
        </div>
        <div className="flex-1 flex flex-col items-center justify-center p-4">
          <div className="text-sm text-red-400 mb-4">{error}</div>
          <button
            onClick={loadFiles}
            className="flex items-center gap-2 px-3 py-1.5 text-sm bg-gray-800 hover:bg-gray-700 rounded"
          >
            <RefreshCw className="w-4 h-4" />
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full glass border-l border-gray-800" data-testid="file-explorer">
      {/* Header */}
      <div className="p-3 border-b border-gray-800 flex justify-between items-center">
        <h3 className="text-sm font-semibold">Workspace Files</h3>
        <div className="flex gap-1">
          <button
            onClick={() => setShowUploadModal(true)}
            className="p-1 hover:bg-gray-800 rounded"
            title="Upload files"
            data-testid="upload-files"
          >
            <Upload className="w-4 h-4" />
          </button>
          <button
            onClick={loadFiles}
            className="p-1 hover:bg-gray-800 rounded"
            title="Refresh files"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={downloadWorkspace}
            className="p-1 hover:bg-gray-800 rounded"
            title="Download workspace as ZIP"
            data-testid="download-workspace"
          >
            <Download className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* File Tree */}
      <div className="flex-1 overflow-y-auto">
        {tree ? (
          tree.children && tree.children.length > 0 ? (
            <div className="p-2">
              {tree.children.map(child => renderNode(child, 0))}
            </div>
          ) : (
            <div className="flex items-center justify-center h-full text-sm text-gray-500">
              No files in workspace
            </div>
          )
        ) : (
          <div className="flex items-center justify-center h-full text-sm text-gray-500">
            No files found
          </div>
        )}
      </div>

      {/* Upload Modal */}
      {showUploadModal && (
        <FileUploadModal
          sessionId={sessionId}
          onClose={() => setShowUploadModal(false)}
          onUploadComplete={loadFiles}
        />
      )}
    </div>
  );
}
