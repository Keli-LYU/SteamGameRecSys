/**
 * SentimentPage Component
 * NLP情感分析实验室界面
 * 
 * 功能:
 * 1. 文本输入框 - 用户输入待分析的文本
 * 2. 提交分析 - 调用后端 /analyze API
 * 3. 结果展示 - 显示情感标签和置信度
 * 4. 历史记录 - 展示过往分析历史
 */
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import '../styles/SentimentPage.css';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function SentimentPage() {
    const [inputText, setInputText] = useState('');
    const [analyzing, setAnalyzing] = useState(false);
    const [currentResult, setCurrentResult] = useState(null);
    const [history, setHistory] = useState([]);
    const [error, setError] = useState(null);

    // 加载历史记录
    useEffect(() => {
        loadHistory();
    }, []);

    const loadHistory = async () => {
        try {
            const response = await axios.get(`${API_BASE_URL}/history?limit=20`);
            setHistory(response.data);
        } catch (err) {
            console.error('Failed to load history:', err);
        }
    };

    // 提交分析
    const handleAnalyze = async (e) => {
        e.preventDefault();

        if (!inputText.trim()) {
            setError('Please enter some text to analyze');
            return;
        }

        try {
            setAnalyzing(true);
            setError(null);

            const response = await axios.post(`${API_BASE_URL}/analyze`, {
                text: inputText
            });

            setCurrentResult(response.data);
            setInputText(''); // 清空输入框

            // 重新加载历史记录
            loadHistory();

        } catch (err) {
            setError(err.response?.data?.detail || 'Analysis failed. Please try again.');
            console.error(err);
        } finally {
            setAnalyzing(false);
        }
    };

    // 获取情感标签的文本
    const getSentimentText = (label) => {
        switch (label.toUpperCase()) {
            case 'POSITIVE':
                return 'POSITIVE';
            case 'NEGATIVE':
                return 'NEGATIVE';
            default:
                return 'NEUTRAL';
        }
    };

    // 获取置信度颜色
    const getConfidenceColor = (confidence) => {
        if (confidence >= 0.8) return '#10b981'; // green
        if (confidence >= 0.6) return '#f59e0b'; // yellow
        return '#ef4444'; // red
    };

    return (
        <div className="sentiment-page">
            <header className="page-header">
                <h1>NLP Sentiment Analysis Lab</h1>
                <p>Powered by BERT - Analyze text sentiment with AI</p>
            </header>

            {/* Analysis Form */}
            <section className="analysis-section">
                <form onSubmit={handleAnalyze} className="analysis-form">
                    <div className="form-group">
                        <label htmlFor="text-input">Enter text to analyze:</label>
                        <textarea
                            id="text-input"
                            className="text-input"
                            rows="6"
                            placeholder="Type or paste your text here... (e.g., game review, comment, feedback)"
                            value={inputText}
                            onChange={(e) => setInputText(e.target.value)}
                            maxLength={5000}
                            disabled={analyzing}
                        />
                        <div className="char-count">
                            {inputText.length} / 5000 characters
                        </div>
                    </div>

                    {error && (
                        <div className="error-message">
                            {error}
                        </div>
                    )}

                    <button
                        type="submit"
                        className="analyze-btn"
                        disabled={analyzing || !inputText.trim()}
                    >
                        {analyzing ? (
                            <>
                                <span className="spinner-small"></span>
                                Analyzing...
                            </>
                        ) : (
                            <>
                                Analyze Sentiment
                            </>
                        )}
                    </button>
                </form>

                {/* Current Result Display */}
                {currentResult && (
                    <div className="result-card">
                        <h3>Analysis Result</h3>
                        <div className="result-content">
                            <div className="sentiment-label">
                                <span className="label-text">{currentResult.label}</span>
                            </div>

                            <div className="confidence-bar">
                                <div className="confidence-label">
                                    Confidence: {(currentResult.confidence * 100).toFixed(1)}%
                                </div>
                                <div className="confidence-track">
                                    <div
                                        className="confidence-fill"
                                        style={{
                                            width: `${currentResult.confidence * 100}%`,
                                            backgroundColor: getConfidenceColor(currentResult.confidence)
                                        }}
                                    />
                                </div>
                            </div>

                            <div className="analyzed-text">
                                <strong>Analyzed text:</strong>
                                <p>"{currentResult.text}"</p>
                            </div>
                        </div>
                    </div>
                )}
            </section>

            {/* History Section */}
            <section className="history-section">
                <h2>Analysis History</h2>

                {history.length === 0 ? (
                    <div className="empty-state">
                        <p>No analysis history yet. Start analyzing text above!</p>
                    </div>
                ) : (
                    <div className="history-list">
                        {history.map((log, idx) => (
                            <div key={log._id || idx} className="history-item">
                                <div className="history-header">
                                    <span className="history-label">{log.label}</span>
                                    <span className="history-confidence">
                                        {(log.confidence * 100).toFixed(0)}%
                                    </span>
                                    <span className="history-date">
                                        {new Date(log.created_at).toLocaleString()}
                                    </span>
                                </div>
                                <div className="history-text">
                                    "{log.text.substring(0, 150)}{log.text.length > 150 ? '...' : ''}"
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </section>
        </div>
    );
}

export default SentimentPage;
