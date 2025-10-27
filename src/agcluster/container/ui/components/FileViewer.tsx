'use client';

import { useState, useEffect, useCallback } from 'react';
import { Copy, Download, AlertTriangle, FileX, X } from 'lucide-react';
import Editor from '@monaco-editor/react';

interface FileViewerProps {
  sessionId: string;
  filePath: string | null;
  onClose?: () => void;
}

interface FileContent {
  path: string;
  content: string;
  language: string;
  size_bytes: number;
  lines: number;
}

const MAX_LINES = 10000;
const MAX_PREVIEW_SIZE = 5 * 1024 * 1024; // 5MB

export function FileViewer({ sessionId, filePath, onClose }: FileViewerProps) {
  const [fileContent, setFileContent] = useState<FileContent | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const loadFile = useCallback(async (path: string) => {
    setLoading(true);
    setError(null);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const apiKey = localStorage.getItem('anthropic_api_key');

      if (!apiKey) {
        throw new Error('No API key found. Please launch an agent from the dashboard first.');
      }

      const res = await fetch(`${apiUrl}/api/files/${sessionId}/${path}`, {
        headers: {
          'Authorization': `Bearer ${apiKey}`
        }
      });

      if (!res.ok) {
        // Get error message from response
        const errorData = await res.json().catch(() => ({ detail: res.statusText }));

        // Special handling for binary files (400 status)
        if (res.status === 400 && errorData.detail?.includes('binary')) {
          throw new Error('Cannot preview binary file. Please use the download button.');
        }

        throw new Error(errorData.detail || `Failed to load file: ${res.statusText}`);
      }

      const data = await res.json();

      // Check if file is too large
      if (data.size_bytes > MAX_PREVIEW_SIZE) {
        throw new Error(`File too large to preview (${(data.size_bytes / 1024 / 1024).toFixed(2)}MB). Maximum size: 5MB`);
      }

      setFileContent(data);
      setLoading(false);
    } catch (error) {
      console.error('Failed to load file:', error);
      setError(error instanceof Error ? error.message : 'Failed to load file');
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    if (filePath) {
      // Skip loading content for images and binary files - they'll be handled separately
      if (isImageFile(filePath) || isBinaryFile(filePath)) {
        setLoading(false);
        setError(null);
        setFileContent(null);
      } else {
        loadFile(filePath);
      }
    } else {
      setFileContent(null);
      setError(null);
    }
  }, [filePath, loadFile]);

  const copyToClipboard = async () => {
    if (!fileContent) return;

    try {
      await navigator.clipboard.writeText(fileContent.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      console.error('Failed to copy to clipboard:', error);
    }
  };

  const downloadFile = async () => {
    if (!filePath) return;

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const apiKey = localStorage.getItem('anthropic_api_key');

      if (!apiKey) {
        console.error('No API key found');
        return;
      }

      const response = await fetch(`${apiUrl}/api/files/${sessionId}/${filePath}/download`, {
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
      a.download = filePath.split('/').pop() || 'file';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Failed to download file:', error);
    }
  };

  const isImageFile = (path: string): boolean => {
    const imageExtensions = ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'svg'];
    const ext = path.split('.').pop()?.toLowerCase();
    return ext ? imageExtensions.includes(ext) : false;
  };

  const isBinaryFile = (path: string): boolean => {
    const binaryExtensions = [
      'pdf', 'zip', 'tar', 'gz', 'rar', '7z',
      'exe', 'dll', 'so', 'dylib',
      'mp3', 'mp4', 'avi', 'mov', 'wav',
      'woff', 'woff2', 'ttf', 'eot', 'ico',
      'db', 'sqlite', 'pyc', 'class'
    ];
    const ext = path.split('.').pop()?.toLowerCase();
    return ext ? binaryExtensions.includes(ext) : false;
  };

  if (!filePath) {
    return (
      <div className="flex flex-col h-full glass border-l border-gray-800" data-testid="file-viewer">
        <div className="flex-1 flex flex-col items-center justify-center text-gray-500">
          <FileX className="w-16 h-16 mb-4 opacity-50" />
          <p className="text-sm">Select a file to view its contents</p>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex flex-col h-full glass border-l border-gray-800" data-testid="file-viewer">
        <div className="p-3 border-b border-gray-800">
          <h3 className="text-sm font-semibold truncate" title={filePath}>{filePath}</h3>
        </div>
        <div className="flex-1 flex items-center justify-center">
          <div className="text-sm text-gray-500">Loading file...</div>
        </div>
      </div>
    );
  }

  if (error) {
    const isBinaryError = error.includes('binary') || error.includes('Cannot preview');

    return (
      <div className="flex flex-col h-full glass border-l border-gray-800" data-testid="file-viewer">
        <div className="p-3 border-b border-gray-800 flex justify-between items-center">
          <h3 className="text-sm font-semibold truncate flex-1" title={filePath}>{filePath}</h3>
          <div className="flex gap-1">
            {isBinaryError && (
              <button
                onClick={downloadFile}
                className="p-1 hover:bg-gray-800 rounded flex items-center gap-1"
                title="Download file"
              >
                <Download className="w-4 h-4" />
                <span className="text-xs">Download</span>
              </button>
            )}
            {onClose && (
              <button
                onClick={onClose}
                className="p-1 hover:bg-gray-800 rounded"
                title="Close file viewer"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
        <div className="flex-1 flex flex-col items-center justify-center p-4">
          <AlertTriangle className="w-12 h-12 text-yellow-400 mb-4" />
          <div className="text-sm text-gray-400 text-center mb-4">{error}</div>
          {!isBinaryError && (
            <button
              onClick={() => loadFile(filePath)}
              className="px-3 py-1.5 text-sm bg-gray-800 hover:bg-gray-700 rounded"
            >
              Retry
            </button>
          )}
        </div>
      </div>
    );
  }

  // Check if image file - show image preview
  if (isImageFile(filePath)) {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const imageUrl = `${apiUrl}/api/files/${sessionId}/${filePath}?raw=true`;

    return (
      <div className="flex flex-col h-full glass border-l border-gray-800" data-testid="file-viewer">
        <div className="p-3 border-b border-gray-800 flex justify-between items-center">
          <h3 className="text-sm font-semibold truncate flex-1" title={filePath}>{filePath}</h3>
          <div className="flex gap-1">
            <button
              onClick={downloadFile}
              className="p-1 hover:bg-gray-800 rounded flex items-center gap-1"
              title="Download image"
            >
              <Download className="w-4 h-4" />
              <span className="text-xs">Download</span>
            </button>
            {onClose && (
              <button
                onClick={onClose}
                className="p-1 hover:bg-gray-800 rounded"
                title="Close file viewer"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
        <div className="flex-1 overflow-auto p-4 flex items-center justify-center bg-black/20">
          <img
            src={imageUrl}
            alt={filePath}
            className="max-w-full max-h-full object-contain"
            onError={(e) => {
              setError('Failed to load image');
            }}
          />
        </div>
      </div>
    );
  }

  // Check if binary file
  if (isBinaryFile(filePath)) {
    return (
      <div className="flex flex-col h-full glass border-l border-gray-800" data-testid="file-viewer">
        <div className="p-3 border-b border-gray-800 flex justify-between items-center">
          <h3 className="text-sm font-semibold truncate flex-1" title={filePath}>{filePath}</h3>
          <div className="flex gap-1">
            <button
              onClick={downloadFile}
              className="p-1 hover:bg-gray-800 rounded"
              title="Download file"
            >
              <Download className="w-4 h-4" />
            </button>
            {onClose && (
              <button
                onClick={onClose}
                className="p-1 hover:bg-gray-800 rounded"
                title="Close file viewer"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
        <div className="flex-1 flex flex-col items-center justify-center p-4 text-gray-500">
          <FileX className="w-16 h-16 mb-4 opacity-50" />
          <p className="text-sm mb-2">Cannot preview binary file</p>
          <p className="text-xs text-gray-600">Click download to save this file</p>
        </div>
      </div>
    );
  }

  if (!fileContent) {
    return null;
  }

  const isLargeFile = fileContent.lines > MAX_LINES;

  return (
    <div className="flex flex-col h-full glass border-l border-gray-800" data-testid="file-viewer">
      {/* Header */}
      <div className="p-3 border-b border-gray-800">
        <div className="flex justify-between items-center mb-2">
          <h3 className="text-sm font-semibold truncate flex-1" title={filePath}>
            {filePath}
          </h3>
          <div className="flex gap-1">
            <button
              onClick={copyToClipboard}
              className="p-1 hover:bg-gray-800 rounded"
              title="Copy to clipboard"
              data-testid="copy-button"
            >
              <Copy className={`w-4 h-4 ${copied ? 'text-green-400' : ''}`} />
            </button>
            <button
              onClick={downloadFile}
              className="p-1 hover:bg-gray-800 rounded"
              title="Download file"
              data-testid="download-button"
            >
              <Download className="w-4 h-4" />
            </button>
            {onClose && (
              <button
                onClick={onClose}
                className="p-1 hover:bg-gray-800 rounded"
                title="Close file viewer"
                data-testid="close-button"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>

        {/* File metadata */}
        <div className="flex gap-4 text-xs text-gray-500">
          <span>{fileContent.lines.toLocaleString()} lines</span>
          <span>{(fileContent.size_bytes / 1024).toFixed(1)} KB</span>
          <span className="capitalize">{fileContent.language}</span>
        </div>

        {/* Warning for large files */}
        {isLargeFile && (
          <div className="mt-2 p-2 bg-yellow-900/20 border border-yellow-700/30 rounded flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 text-yellow-400 flex-shrink-0 mt-0.5" />
            <div className="text-xs text-yellow-400">
              <p className="font-semibold">Large file warning</p>
              <p>This file has {fileContent.lines.toLocaleString()} lines. Only showing first {MAX_LINES.toLocaleString()} lines for performance.</p>
            </div>
          </div>
        )}
      </div>

      {/* Monaco Editor */}
      <div className="flex-1 overflow-hidden" data-testid="monaco-editor">
        <Editor
          height="100%"
          language={fileContent.language}
          value={isLargeFile
            ? fileContent.content.split('\n').slice(0, MAX_LINES).join('\n')
            : fileContent.content
          }
          theme="vs-dark"
          options={{
            readOnly: true,
            minimap: { enabled: true },
            fontSize: 13,
            lineNumbers: 'on',
            scrollBeyondLastLine: false,
            automaticLayout: true,
            wordWrap: 'off',
            scrollbar: {
              vertical: 'visible',
              horizontal: 'visible',
              useShadows: false,
              verticalScrollbarSize: 10,
              horizontalScrollbarSize: 10
            },
            find: {
              addExtraSpaceOnTop: false,
              autoFindInSelection: 'never',
              seedSearchStringFromSelection: 'never'
            }
          }}
          loading={
            <div className="flex items-center justify-center h-full">
              <div className="text-sm text-gray-500">Loading editor...</div>
            </div>
          }
        />
      </div>
    </div>
  );
}
