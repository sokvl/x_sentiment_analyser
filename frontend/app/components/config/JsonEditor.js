'use client';
import React, { useState, useEffect } from 'react';

// Importujemy sam edytor i np. locale (język)
import JSONInput from 'react-json-editor-ajrm';
import locale from 'react-json-editor-ajrm/locale/en';


export default function JsonEditor({
  initialConfig,
  onCancel,
  onSave,
}) {
  const [internalJson, setInternalJson] = useState(null);

  useEffect(() => {
    if (initialConfig) {
      setInternalJson(initialConfig);
    }
  }, [initialConfig]);

  const handleSave = () => {
    if (internalJson) {
      onSave(internalJson);
    } else {
      alert('No valid JSON data found.');
    }
  };

  return (
    <div className="bg-gray-800 p-4 rounded shadow-lg">
      <h2 className="text-xl font-bold mb-4">JSON Editor</h2>

      {/* Sam edytor JSON */}
      <JSONInput
        id="json_editor"
        locale={locale}
        theme="dark_vscode"  // Dostępne też np. "light_vscode", "dark_vscode" i inne
        // placeholder -> JSON początkowy
        placeholder={internalJson}
        height="400px"
        onChange={(content) => {
          // content zawiera m.in. content.jsObject
          // jeżeli jest poprawny JSON, to tam będzie sparsowany obiekt
          // jeżeli niepoprawny, to content.jsObject będzie null/undefined
          if (content.jsObject) {
            setInternalJson(content.jsObject);
          }
        }}
        // Możesz dodać inne props, np. "onKeyPressUpdate={true}" itp.
      />

      <div className="mt-4 flex gap-4">
        <button
          onClick={handleSave}
          className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded"
        >
          Save JSON
        </button>
        <button
          onClick={onCancel}
          className="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}
