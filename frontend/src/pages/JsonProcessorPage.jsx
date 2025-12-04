import React, { useState } from 'react';

const JsonProcessorPage = () => {
  const [formData, setFormData] = useState({ name: '', age: '', message: '' });
  const [response, setResponse] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleChange = (e) => setFormData({ ...formData, [e.target.name]: e.target.value });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      // Make sure your Python backend is running on port 8000
      const res = await fetch('http://localhost:8000/process-user-data', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...formData, age: parseInt(formData.age) }),
      });
      const data = await res.json();
      setResponse(data);
    } catch (err) {
      setError("Failed to connect to backend");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8 max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold mb-6 text-light-text dark:text-dark-text">Backend API Tester</h1>
      
      <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-md">
        <form onSubmit={handleSubmit} className="space-y-4">
          <input className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600" name="name" placeholder="Name" onChange={handleChange} />
          <input className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600" name="age" type="number" placeholder="Age" onChange={handleChange} />
          <input className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600" name="message" placeholder="Message" onChange={handleChange} />
          
          <button type="submit" className="w-full bg-[var(--color-accent)] text-white p-2 rounded hover:opacity-90">
            {loading ? 'Sending...' : 'Send to Python'}
          </button>
        </form>

        {response && (
          <div className="mt-6 p-4 bg-green-50 dark:bg-green-900/20 rounded border border-green-200">
            <pre className="text-sm">{JSON.stringify(response, null, 2)}</pre>
          </div>
        )}
      </div>
    </div>
  );
};

export default JsonProcessorPage;