import React, { useState, useEffect, useRef, useCallback } from 'react';
import { 
  Search, Calendar, Tag, RefreshCw, CheckCircle, AlertCircle, 
  Bell, Trash2, X, GraduationCap, Clock, 
  Activity, Server, LayoutGrid, Sun, Moon, Database, 
  Eye, HardDrive, Zap, HelpCircle, 
  UploadCloud, FilePlus, Globe, History, ChevronRight
} from 'lucide-react';
import { 
  PieChart, Pie, Cell, ResponsiveContainer, BarChart, Bar, XAxis, Tooltip as RechartsTooltip, Legend 
} from 'recharts';

// --- TYPES ---
interface SearchResult {
  id: string;
  title: string;
  content: string;
  source_url: string;
  date: string;
  relevance_score: number;
  category?: string;
}

interface NotificationItem {
  id: number;
  type: 'success' | 'error';
  message: string;
  timestamp: number;
}

interface SystemStats {
  total_documents: number;
  storage_used: string;
  system_health: string;
  latency: string;
}

// --- COMPONENTS ---

const CountUp = ({ end, duration = 1000, suffix = "" }: { end: number, duration?: number, suffix?: string }) => {
  const [count, setCount] = useState(0);

  useEffect(() => {
    let startTime: number | null = null;
    let animationFrameId: number;

    const animate = (timestamp: number) => {
      if (!startTime) startTime = timestamp;
      const progress = Math.min((timestamp - startTime) / duration, 1);
      const ease = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress);
      setCount(Math.floor(ease * end));
      if (progress < 1) animationFrameId = requestAnimationFrame(animate);
    };

    animationFrameId = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(animationFrameId);
  }, [end, duration]);

  return <span>{count.toLocaleString()}{suffix}</span>;
};

const SkeletonCard = () => (
  <div className="rounded-2xl p-6 border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm animate-pulse">
    <div className="flex justify-between mb-4">
      <div className="h-6 bg-slate-200 dark:bg-slate-800 rounded w-1/3"></div>
      <div className="flex gap-2">
        <div className="h-6 bg-slate-200 dark:bg-slate-800 rounded w-16"></div>
        <div className="h-6 bg-slate-200 dark:bg-slate-800 rounded w-16"></div>
      </div>
    </div>
    <div className="space-y-2">
      <div className="h-4 bg-slate-200 dark:bg-slate-800 rounded w-full"></div>
      <div className="h-4 bg-slate-200 dark:bg-slate-800 rounded w-5/6"></div>
      <div className="h-4 bg-slate-200 dark:bg-slate-800 rounded w-4/6"></div>
    </div>
  </div>
);

// --- MAIN PAGE ---

const SearchPage: React.FC = () => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [scrapeUrl, setScrapeUrl] = useState('');
  const [showScrapeModal, setShowScrapeModal] = useState(false);
  
  // HISTORY STATE
  const [searchHistory, setSearchHistory] = useState<string[]>([]);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  const [stats, setStats] = useState<SystemStats>({
    total_documents: 0, storage_used: "0 MB", system_health: "Checking...", latency: "0ms"
  });

  const [previewDoc, setPreviewDoc] = useState<SearchResult | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [toast, setToast] = useState<{show: boolean, type: 'success' | 'error', message: string}>({
    show: false, type: 'success', message: ''
  });

  const [isDarkMode, setIsDarkMode] = useState(() => {
    const saved = localStorage.getItem('app_theme');
    return saved ? saved === 'dark' : true;
  });

  const [isDragging, setIsDragging] = useState(false);

  // --- EFFECTS ---

  useEffect(() => {
    localStorage.setItem('app_theme', isDarkMode ? 'dark' : 'light');
    if (isDarkMode) document.body.classList.add('dark');
    else document.body.classList.remove('dark');
  }, [isDarkMode]);

  // Load History on Mount
  useEffect(() => {
    const savedHistory = localStorage.getItem('campus_search_history');
    if (savedHistory) {
      setSearchHistory(JSON.parse(savedHistory));
    }
  }, []);

  const fetchStats = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/stats');
      const data = await response.json();
      setStats(data);
    } catch (error) {
      console.error("Failed to fetch stats", error);
    }
  };

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 30000); 
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (toast.show) {
      const timer = setTimeout(() => setToast(prev => ({ ...prev, show: false })), 5000);
      return () => clearTimeout(timer);
    }
  }, [toast.show]);

  // --- HELPERS ---

  const addNotification = useCallback((type: 'success' | 'error', message: string) => {
    const newNote: NotificationItem = { id: Date.now(), type, message, timestamp: Date.now() };
    setNotifications(prev => {
        const updated = [newNote, ...prev];
        return updated.slice(0, 10);
    });
    setToast({ show: true, type, message });
  }, []);

  const clearNotifications = () => setNotifications([]);

  const saveToHistory = (searchTerm: string) => {
    if (!searchTerm.trim()) return;
    const newHistory = [searchTerm, ...searchHistory.filter(h => h !== searchTerm)].slice(0, 15);
    setSearchHistory(newHistory);
    localStorage.setItem('campus_search_history', JSON.stringify(newHistory));
  };

  const removeFromHistory = (e: React.MouseEvent, term: string) => {
    e.stopPropagation();
    const newHistory = searchHistory.filter(h => h !== term);
    setSearchHistory(newHistory);
    localStorage.setItem('campus_search_history', JSON.stringify(newHistory));
  };

  const clearHistory = () => {
    if(window.confirm("Clear all search history?")) {
        setSearchHistory([]);
        localStorage.removeItem('campus_search_history');
    }
  };

  // --- HANDLERS ---

  const handleScrape = async () => {
    if (!scrapeUrl) return;
    setShowScrapeModal(false);
    addNotification('success', 'Scraper started. Check back soon.');
    try {
      await fetch('http://localhost:8000/api/trigger-scrape', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: scrapeUrl })
      });
    } catch (error) {
        console.error(error);
        addNotification('error', 'Scraper failed to start.');
    }
  };

  const handleScan = async () => {
    setScanning(true);
    try {
      const response = await fetch('http://localhost:8000/api/scan', { method: 'POST' });
      const data = await response.json();
      if (data.status === 'success') {
        addNotification('success', data.message);
        fetchStats(); 
      } else {
        addNotification('error', data.message);
      }
    } catch (error) {
      console.error(error);
      addNotification('error', 'Failed to connect to backend.');
    } finally {
      setScanning(false);
    }
  };

  const runSearch = async (searchTerm: string) => {
    if (!searchTerm.trim()) return;
    setLoading(true);
    setResults([]);
    setQuery(searchTerm);
    saveToHistory(searchTerm); // Save to history
    
    await new Promise(resolve => setTimeout(resolve, 400)); // Small delay for UX

    try {
      const response = await fetch('http://localhost:8000/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: searchTerm, limit: 15 })
      });
      const data = await response.json();
      setResults(data);
    } catch (error) {
      console.error(error);
      addNotification('error', 'Search failed.');
    } finally {
      setLoading(false);
    }
  };

  const handleSearchForm = (e: React.FormEvent) => {
    e.preventDefault();
    runSearch(query);
  };

  const processFiles = async (files: File[]) => {
    if (files.length === 0) return;
    setScanning(true);
    let successCount = 0;
    for (const file of files) {
        const formData = new FormData();
        formData.append('file', file);
        try {
            const response = await fetch('http://localhost:8000/api/upload', {
                method: 'POST',
                body: formData
            });
            const data = await response.json();
            if (data.status === 'success') successCount++;
        } catch (error) {
            console.error("Upload error", error);
        }
    }
    setScanning(false);
    if (successCount > 0) {
        addNotification('success', `Processed ${successCount} files.`);
        fetchStats(); 
    } else {
        addNotification('error', 'Upload failed.');
    }
  };

  const handleDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const files = Array.from(e.dataTransfer.files);
    await processFiles(files);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      await processFiles(Array.from(e.target.files));
    }
  };

  const handleDelete = async (sourceUrl: string) => {
    if (!window.confirm("Delete this document?")) return;
    const filename = sourceUrl.split('/').pop();
    if (!filename) return;
    try {
      const response = await fetch(`http://localhost:8000/api/documents/${filename}`, { method: 'DELETE' });
      if (response.ok) {
        addNotification('success', 'Deleted.');
        setResults(prev => prev.filter(r => r.source_url !== sourceUrl));
        if (previewDoc?.source_url === sourceUrl) setPreviewDoc(null);
        fetchStats(); 
      } else {
        addNotification('error', 'Failed to delete.');
      }
    } catch (error) {
      console.error(error);
      addNotification('error', 'Error deleting document.');
    }
  };

  const renderSnippet = (text: string, query: string) => {
    if (!query.trim()) return text.slice(0, 150) + '...';
    const lowerText = text.toLowerCase();
    const lowerQuery = query.toLowerCase();
    const index = lowerText.indexOf(lowerQuery);
    if (index === -1) return text.slice(0, 150) + '...';
    const start = Math.max(0, index - 80);
    const end = Math.min(text.length, index + lowerQuery.length + 150);
    const snippet = text.slice(start, end);
    const parts = snippet.split(new RegExp(`(${query})`, 'gi'));
    return parts.map((part, i) => 
      part.toLowerCase() === query.toLowerCase() ? 
        <span key={i} className={`font-bold px-1 rounded ${isDarkMode ? "bg-yellow-500/30 text-yellow-200 border-b border-yellow-500" : "bg-yellow-200 text-gray-900"}`}>{part}</span> : part
    );
  };

  const formatTime = (timestamp: number) => {
    return new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const pieData = [
    { name: 'Exams', value: 35, color: '#3b82f6' },
    { name: 'Fees', value: 25, color: '#10b981' },
    { name: 'Hostel', value: 20, color: '#f59e0b' },
    { name: 'General', value: 20, color: '#6366f1' },
  ];

  const barData = [
    { name: 'Mon', files: 12 },
    { name: 'Tue', files: 19 },
    { name: 'Wed', files: 8 },
    { name: 'Thu', files: 25 },
    { name: 'Fri', files: 15 },
  ];

  const theme = {
    bg: isDarkMode ? "bg-slate-950" : "bg-gray-50",
    text: isDarkMode ? "text-slate-200" : "text-gray-700",
    header: isDarkMode ? "bg-slate-900/80 border-slate-800" : "bg-white/90 border-gray-200",
    card: isDarkMode ? "bg-slate-900 border-slate-800" : "bg-white border-gray-200 shadow-sm",
    statCard: isDarkMode ? "bg-slate-900/50 border-slate-800" : "bg-white border-gray-200 shadow-sm",
    inputBg: isDarkMode ? "bg-slate-900 border-slate-700 text-white placeholder-slate-500" : "bg-white border-gray-200 text-gray-900 placeholder-gray-400 shadow-sm",
    progressBarBg: isDarkMode ? "bg-slate-800" : "bg-gray-200",
    divider: isDarkMode ? "border-slate-800" : "border-gray-200",
    iconBtn: isDarkMode ? "text-slate-400 hover:text-white hover:bg-slate-800" : "text-gray-500 hover:text-blue-600 hover:bg-gray-100",
    dropdown: isDarkMode ? "bg-slate-900 border-slate-700" : "bg-white border-gray-200 shadow-xl",
    dropdownItem: isDarkMode ? "hover:bg-slate-800/50 border-slate-800" : "hover:bg-gray-50 border-gray-100",
    sidebar: isDarkMode ? "bg-slate-900 border-slate-800" : "bg-white border-gray-200",
  };

  return (
    <div className={`min-h-screen font-sans transition-colors duration-300 flex ${theme.bg} ${theme.text}`} onClick={() => setShowDropdown(false)}>
      
      {/* --- SIDEBAR --- */}
      <aside 
        className={`fixed inset-y-0 left-0 z-30 w-64 transform transition-transform duration-300 ease-in-out border-r flex flex-col ${theme.sidebar} ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full'} md:relative md:translate-x-0`}
      >
        <div className="p-6 flex items-center gap-3 border-b border-opacity-10 border-gray-500">
           <div className="p-2 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-lg shadow-lg">
             <GraduationCap className="text-white" size={20} />
           </div>
           <h1 className="font-bold text-lg tracking-tight">Campus Insight</h1>
        </div>

        <div className="flex-1 overflow-y-auto p-4">
            <div className="mb-6">
                <button onClick={() => runSearch("")} className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl mb-2 font-medium transition-colors ${!query && results.length === 0 ? 'bg-blue-600 text-white' : 'hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500'}`}>
                    <LayoutGrid size={18} /> Dashboard
                </button>
            </div>

            <div className="mb-2 px-4 flex justify-between items-center text-xs font-semibold text-slate-500 uppercase tracking-wider">
                <span>Recent Searches</span>
                {searchHistory.length > 0 && <button onClick={clearHistory} className="hover:text-red-500">Clear</button>}
            </div>
            
            <div className="space-y-1">
                {searchHistory.length === 0 ? (
                    <div className="px-4 py-4 text-sm text-slate-400 italic">No recent searches</div>
                ) : (
                    searchHistory.map((item, i) => (
                        <div key={i} onClick={() => runSearch(item)} className={`group flex items-center justify-between px-4 py-2.5 rounded-lg cursor-pointer text-sm transition-colors ${theme.text} hover:bg-slate-100 dark:hover:bg-slate-800`}>
                            <div className="flex items-center gap-3 overflow-hidden">
                                <History size={14} className="opacity-50 flex-shrink-0"/>
                                <span className="truncate">{item}</span>
                            </div>
                            <button onClick={(e) => removeFromHistory(e, item)} className="opacity-0 group-hover:opacity-100 text-slate-400 hover:text-red-500">
                                <X size={14} />
                            </button>
                        </div>
                    ))
                )}
            </div>
        </div>

        <div className="p-4 border-t border-opacity-10 border-gray-500 text-xs text-slate-500 text-center">
            v3.0.1 • Local Storage Active
        </div>
      </aside>

      {/* --- MAIN CONTENT --- */}
      <div className="flex-1 flex flex-col h-screen overflow-hidden relative">
        
        {/* HEADER */}
        <header className={`backdrop-blur-md border-b sticky top-0 z-20 px-6 py-4 flex justify-between items-center ${theme.header}`}>
            <div className="flex items-center gap-4">
                <button className="md:hidden p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800" onClick={() => setIsSidebarOpen(!isSidebarOpen)}>
                    <ChevronRight size={20} className={`transform transition-transform ${isSidebarOpen ? 'rotate-180' : '0'}`}/>
                </button>
                <h2 className="font-semibold text-lg opacity-80 hidden md:block">{query ? `Results for "${query}"` : 'Dashboard'}</h2>
            </div>

            <div className="flex items-center gap-3">
                <button onClick={() => setShowScrapeModal(true)} className={`hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-lg border text-sm font-medium ${isDarkMode ? 'bg-slate-800 hover:bg-slate-700 border-slate-700' : 'bg-white hover:bg-gray-50 border-gray-200'}`}>
                  <Globe size={14} className="text-emerald-500" /> Live Scrape
                </button>
                <button onClick={() => setIsDarkMode(!isDarkMode)} className="p-2 rounded-full text-slate-400 hover:text-white transition-colors">
                  {isDarkMode ? <Sun size={20} /> : <Moon size={20} />}
                </button>
                <button onClick={handleScan} disabled={scanning} className={`p-2 rounded-full text-slate-400 hover:text-blue-500 transition-colors ${scanning ? 'animate-spin' : ''}`}>
                  <RefreshCw size={20} />
                </button>
                <div className="relative">
                  <button onClick={(e) => { e.stopPropagation(); setShowDropdown(!showDropdown); }} className={`p-2 rounded-full relative transition-colors ${theme.iconBtn}`}>
                    <Bell size={20} />
                    {notifications.length > 0 && <span className="absolute top-1 right-1 w-2.5 h-2.5 bg-red-500 rounded-full ring-2 ring-white dark:ring-slate-900 animate-pulse"></span>}
                  </button>
                  {showDropdown && (
                    <div className={`absolute right-0 mt-3 w-80 rounded-xl border overflow-hidden z-50 animate-in fade-in slide-in-from-top-2 duration-200 ${theme.dropdown}`}>
                      <div className={`p-3 border-b flex justify-between items-center ${isDarkMode ? 'bg-slate-900/50 border-slate-700' : 'bg-gray-50 border-gray-100'}`}>
                        <h3 className={`font-semibold text-sm ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>Notifications</h3>
                        {notifications.length > 0 && <button onClick={clearNotifications} className="text-xs text-red-500 hover:text-red-600 flex items-center gap-1 transition-colors"><Trash2 size={12}/> Clear</button>}
                      </div>
                      <div className="max-h-64 overflow-y-auto">
                        {notifications.length === 0 ? (
                          <div className={`p-8 text-center text-sm ${isDarkMode ? 'text-slate-500' : 'text-gray-400'}`}>No new notifications</div>
                        ) : (
                          notifications.map(note => (
                            <div key={note.id} className={`p-3 border-b transition-colors flex gap-3 items-start ${theme.dropdownItem}`}>
                              <div className={`mt-1 ${note.type === 'success' ? 'text-emerald-500' : 'text-red-500'}`}>
                                {note.type === 'success' ? <CheckCircle size={16}/> : <AlertCircle size={16}/>}
                              </div>
                              <div>
                                <p className={`text-sm leading-snug ${theme.text}`}>{note.message}</p>
                                <p className={`text-xs mt-1 flex items-center gap-1 opacity-60`}><Clock size={10} /> {formatTime(note.timestamp)}</p>
                              </div>
                            </div>
                          ))
                        )}
                      </div>
                    </div>
                  )}
                </div>
            </div>
        </header>

        {/* SCROLLABLE BODY */}
        <main className="flex-1 overflow-y-auto p-4 md:p-8 scroll-smooth">
            <div className="max-w-5xl mx-auto w-full">
                
                {/* SEARCH INPUT */}
                <div className="flex flex-col items-center justify-center mb-8">
                  <div 
                    className={`w-full relative rounded-2xl border-2 border-dashed transition-all duration-300 ${isDragging ? 'border-blue-500 bg-blue-500/10' : theme.inputBg} ${isDarkMode ? 'border-slate-700' : 'border-gray-300'}`}
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    onDrop={handleDrop}
                  >
                    {isDragging ? (
                       <div className="py-8 flex flex-col items-center justify-center text-blue-500 animate-pulse">
                          <UploadCloud size={48} />
                          <p className="mt-2 font-bold text-lg">Drop files to upload instantly</p>
                       </div>
                    ) : (
                      <form onSubmit={handleSearchForm} className="relative flex items-center overflow-hidden">
                        <div className="pl-6 text-slate-400"><Search size={24} /></div>
                        <input
                          type="text" value={query} onChange={(e) => setQuery(e.target.value)}
                          placeholder="Search documents (or drag & drop files)..."
                          className="w-full py-5 px-4 text-lg bg-transparent focus:outline-none font-medium"
                        />
                        <input type="file" multiple className="hidden" ref={fileInputRef} onChange={handleFileSelect} />
                        <button type="button" onClick={() => fileInputRef.current?.click()} className={`mx-2 p-2 rounded-lg transition-colors ${isDarkMode ? 'hover:bg-slate-700 text-slate-400' : 'hover:bg-gray-100 text-gray-500'}`} title="Upload Files"><FilePlus size={20} /></button>
                        <button type="submit" disabled={loading} className="mx-2 px-6 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-xl font-semibold transition-all">{loading ? 'Searching...' : 'Search'}</button>
                      </form>
                    )}
                  </div>
                </div>

                {/* RESULTS */}
                {loading ? (
                  <div className="space-y-6">
                    <SkeletonCard /><SkeletonCard /><SkeletonCard />
                  </div>
                ) : results.length > 0 ? (
                  <div className="space-y-6 animate-in slide-in-from-bottom-4">
                    <div className="flex items-center justify-between px-2">
                       <span className="text-sm font-medium opacity-70">Found {results.length} relevant documents</span>
                       <span className={`text-xs px-2 py-1 rounded border ${isDarkMode ? 'bg-slate-900 border-slate-700' : 'bg-white border-gray-200'}`}>Smart Filter Active</span>
                    </div>
                    {results.map((result) => (
                      <div key={result.id} className={`group rounded-2xl p-6 border transition-all ${theme.card} hover:border-blue-500/50`}>
                        <div className="flex justify-between items-start mb-3">
                          <h3 className={`text-xl font-bold group-hover:text-blue-500 transition-colors ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>{result.title}</h3>
                          <div className="flex gap-2">
                            <span className={`px-3 py-1 rounded-full text-xs font-medium border flex items-center gap-1 ${isDarkMode ? 'bg-slate-800 text-blue-400 border-slate-700' : 'bg-blue-50 text-blue-700 border-blue-100'}`}><Calendar size={12} /> {result.date}</span>
                            <span className={`px-3 py-1 rounded-full text-xs font-medium border flex items-center gap-1 ${isDarkMode ? 'bg-slate-800 text-slate-400 border-slate-700' : 'bg-gray-100 text-gray-600 border-gray-200'}`}><Tag size={12} /> {result.category}</span>
                          </div>
                        </div>
                        <p className="pl-4 py-2 border-l-2 border-blue-500/30 leading-relaxed font-serif text-lg opacity-90">{renderSnippet(result.content, query)}</p>
                        <div className="mt-4 pt-4 border-t border-slate-800/50 flex justify-between items-center">
                          <span className="text-xs text-slate-500 truncate max-w-md">{result.source_url}</span>
                          <div className="flex gap-3">
                            <button onClick={() => handleDelete(result.source_url)} className="text-red-500 hover:text-red-400 text-sm font-medium flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity"><Trash2 size={16} /> Delete</button>
                            <button onClick={() => setPreviewDoc(result)} className="text-blue-500 hover:text-blue-400 text-sm font-medium flex items-center gap-1"><Eye size={16} /> View</button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  !query && (
                    <div className="animate-in fade-in duration-700 space-y-6">
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div className={`p-4 rounded-xl border flex items-center gap-4 ${theme.statCard}`}>
                            <div className={`p-3 rounded-lg bg-opacity-10 ${isDarkMode ? 'bg-white' : 'bg-black'} text-blue-500`}><Database size={20} /></div>
                            <div><div className="text-xs font-bold uppercase tracking-wider opacity-60">Total Indexed</div><div className={`text-xl font-bold ${isDarkMode ? 'text-white' : 'text-gray-900'}`}><CountUp end={stats.total_documents} /></div></div>
                        </div>
                        <div className={`p-4 rounded-xl border flex items-center gap-4 ${theme.statCard}`}>
                            <div className={`p-3 rounded-lg bg-opacity-10 ${isDarkMode ? 'bg-white' : 'bg-black'} text-purple-500`}><HardDrive size={20} /></div>
                            <div><div className="text-xs font-bold uppercase tracking-wider opacity-60">Storage Used</div><div className={`text-xl font-bold ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>{stats.storage_used}</div></div>
                        </div>
                        <div className={`p-4 rounded-xl border flex items-center gap-4 ${theme.statCard}`}>
                            <div className={`p-3 rounded-lg bg-opacity-10 ${isDarkMode ? 'bg-white' : 'bg-black'} text-emerald-500`}><Activity size={20} /></div>
                            <div><div className="text-xs font-bold uppercase tracking-wider opacity-60">System Health</div><div className={`text-xl font-bold ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>{stats.system_health}</div></div>
                        </div>
                        <div className={`p-4 rounded-xl border flex items-center gap-4 ${theme.statCard}`}>
                            <div className={`p-3 rounded-lg bg-opacity-10 ${isDarkMode ? 'bg-white' : 'bg-black'} text-orange-500`}><Zap size={20} /></div>
                            <div><div className="text-xs font-bold uppercase tracking-wider opacity-60">Avg Latency</div><div className={`text-xl font-bold ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>{stats.latency}</div></div>
                        </div>
                      </div>
                      
                      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                        <div className={`p-6 rounded-2xl border ${theme.card}`}>
                          <h3 className={`text-lg font-bold mb-6 flex items-center gap-2 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}><LayoutGrid size={18} className="text-blue-500"/> Document Categories</h3>
                          <div className="h-48 w-full">
                            <ResponsiveContainer width="100%" height="100%">
                              <PieChart>
                                <Pie data={pieData} cx="50%" cy="50%" innerRadius={40} outerRadius={70} paddingAngle={5} dataKey="value">
                                  {pieData.map((entry, index) => <Cell key={`cell-${index}`} fill={entry.color} strokeWidth={0} />)}
                                </Pie>
                                <RechartsTooltip contentStyle={{ backgroundColor: isDarkMode ? '#1e293b' : '#fff', borderRadius: '8px', border: 'none' }} />
                                <Legend />
                              </PieChart>
                            </ResponsiveContainer>
                          </div>
                        </div>
                        
                        <div className={`p-6 rounded-2xl border ${theme.card}`}>
                          <h3 className={`text-lg font-bold mb-6 flex items-center gap-2 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}><Activity size={18} className="text-purple-500"/> Weekly Activity</h3>
                          <div className="h-48 w-full">
                            <ResponsiveContainer width="100%" height="100%">
                              <BarChart data={barData}>
                                <XAxis dataKey="name" stroke={isDarkMode ? "#64748b" : "#94a3b8"} fontSize={12} tickLine={false} axisLine={false} />
                                <RechartsTooltip cursor={{fill: 'transparent'}} contentStyle={{ backgroundColor: isDarkMode ? '#1e293b' : '#fff', borderRadius: '8px', border: 'none' }} />
                                <Bar dataKey="files" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
                              </BarChart>
                            </ResponsiveContainer>
                          </div>
                        </div>

                        <div className={`p-6 rounded-2xl border flex flex-col ${theme.card}`}>
                           <h3 className={`text-lg font-bold mb-4 flex items-center gap-2 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}><Server size={18} className="text-emerald-500"/> Live Status</h3>
                           <div className="space-y-4 mb-6">
                              <div><div className="flex justify-between text-xs mb-1 opacity-70"><span>Database Load</span><span>45%</span></div><div className={`h-2 rounded-full w-full ${theme.progressBarBg}`}><div className="h-full rounded-full bg-blue-500 w-[45%]"></div></div></div>
                              <div><div className="flex justify-between text-xs mb-1 opacity-70"><span>API Quota</span><span>12%</span></div><div className={`h-2 rounded-full w-full ${theme.progressBarBg}`}><div className="h-full rounded-full bg-emerald-500 w-[12%]"></div></div></div>
                           </div>
                           <div className={`mt-auto p-4 rounded-xl border ${isDarkMode ? 'bg-slate-950 border-slate-800' : 'bg-blue-50 border-blue-100'}`}>
                              <div className="flex items-start gap-3">
                                 <HelpCircle size={18} className="text-blue-500 mt-0.5" />
                                 <div>
                                   <div className={`text-sm font-bold mb-1 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>Pro Tip</div>
                                   <p className="text-xs opacity-70 leading-relaxed">Click history items on the left to quickly re-run past searches.</p>
                                 </div>
                              </div>
                           </div>
                        </div>
                      </div>
                    </div>
                  )
                )}
            </div>
        </main>
      </div>
      
      {/* SCRAPE MODAL */}
      {showScrapeModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in">
           <div className={`w-full max-w-lg rounded-2xl p-6 border ${theme.card}`}>
               <h3 className={`text-xl font-bold mb-4 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>Connect Website</h3>
               <p className="text-sm opacity-70 mb-4">Enter a URL (e.g., your college notice board). We will fetch all PDFs and Images.</p>
               <input type="text" value={scrapeUrl} onChange={(e) => setScrapeUrl(e.target.value)} placeholder="https://college.edu/notices" className={`w-full p-3 rounded-lg border mb-4 ${theme.inputBg}`} />
               <div className="flex justify-end gap-3">
                   <button onClick={() => setShowScrapeModal(false)} className="px-4 py-2 rounded-lg text-sm hover:bg-slate-800">Cancel</button>
                   <button onClick={handleScrape} className="px-4 py-2 rounded-lg text-sm bg-emerald-600 text-white hover:bg-emerald-500">Start Scraper</button>
               </div>
           </div>
        </div>
      )}

      {/* TOAST */}
      {toast.show && (
        <div className={`fixed bottom-6 right-6 max-w-sm w-full rounded-xl shadow-2xl border-l-4 p-4 flex items-start gap-3 z-50 animate-in slide-in-from-right-5 ${isDarkMode ? 'bg-slate-900 border-emerald-500' : 'bg-white border-emerald-500'}`}>
           <CheckCircle className="text-emerald-500" size={20} />
           <p className={`text-sm ${theme.text}`}>{toast.message}</p>
        </div>
      )}
      
      {/* PREVIEW MODAL */}
      {previewDoc && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className={`w-full max-w-4xl h-[85vh] rounded-2xl flex flex-col overflow-hidden border ${isDarkMode ? 'bg-slate-900 border-slate-700' : 'bg-white border-gray-200'}`}>
            <div className="p-4 border-b border-slate-700 flex justify-between items-center">
              <div><h3 className={`font-bold ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>{previewDoc.title}</h3></div>
              <button onClick={() => setPreviewDoc(null)} className="p-2 hover:bg-slate-800 rounded-full"><X size={24} className="text-slate-400" /></button>
            </div>
            <div className="flex-1 bg-slate-950 flex items-center justify-center overflow-auto p-4">
              {previewDoc.source_url.endsWith('.pdf') ? <iframe src={previewDoc.source_url} className="w-full h-full rounded-lg" title="Preview" /> : <img src={previewDoc.source_url} alt="Doc" className="max-w-full max-h-full object-contain" />}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SearchPage;