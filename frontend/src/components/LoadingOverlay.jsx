import { motion, AnimatePresence } from 'framer-motion';

export default function LoadingOverlay({ isVisible, phase, progress, message }) {
    return (
        <AnimatePresence>
            {isVisible && (
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    style={{
                        position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
                        background: 'rgba(3, 7, 18, 0.85)',
                        backdropFilter: 'blur(12px)',
                        WebkitBackdropFilter: 'blur(12px)',
                        zIndex: 9999,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        padding: 24
                    }}
                >
                    <motion.div
                        initial={{ scale: 0.9, opacity: 0, y: 20 }}
                        animate={{ scale: 1, opacity: 1, y: 0 }}
                        exit={{ scale: 0.9, opacity: 0, y: 20 }}
                        className="card glass-card"
                        style={{ 
                            maxWidth: 480, 
                            width: '100%', 
                            textAlign: 'center', 
                            padding: '48px 32px',
                            boxShadow: '0 0 50px rgba(99, 102, 241, 0.15)',
                            border: '1px solid rgba(255, 255, 255, 0.1)'
                        }}
                    >
                        {/* Animated Logo/Spinner */}
                        <div style={{ position: 'relative', width: 80, height: 80, margin: '0 auto 32px' }}>
                            <motion.div
                                animate={{ rotate: 360 }}
                                transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                                style={{
                                    width: '100%', height: '100%',
                                    borderRadius: '50%',
                                    border: '3px solid transparent',
                                    borderTopColor: 'var(--color-primary)',
                                    borderRightColor: 'var(--color-primary-light)',
                                    boxShadow: '0 0 20px rgba(99, 102, 241, 0.4)'
                                }}
                            />
                            <motion.div
                                animate={{ scale: [1, 1.2, 1] }}
                                transition={{ duration: 2, repeat: Infinity }}
                                style={{
                                    position: 'absolute', inset: 0,
                                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                                    fontSize: 32
                                }}
                            >
                                🧠
                            </motion.div>
                        </div>

                        <h3 style={{ 
                            fontFamily: 'Space Grotesk, sans-serif',
                            fontSize: 24, 
                            fontWeight: 700, 
                            marginBottom: 12,
                            background: 'var(--gradient-primary)',
                            WebkitBackgroundClip: 'text',
                            WebkitTextFillColor: 'transparent'
                        }}>
                            {phase || 'Processing...'}
                        </h3>
                        
                        <p style={{ color: 'var(--color-text-muted)', marginBottom: 32, fontSize: 15, lineHeight: 1.6 }}>
                            {message || 'Our AI is analyzing your documents to ensure the highest accuracy. Please stay on this page.'}
                        </p>

                        {progress !== undefined && (
                            <div style={{ width: '100%' }}>
                                <div className="progress-bar" style={{ height: 8, background: 'rgba(255,255,255,0.05)', borderRadius: 4, overflow: 'hidden', marginBottom: 12 }}>
                                    <motion.div
                                        initial={{ width: 0 }}
                                        animate={{ width: `${progress}%` }}
                                        transition={{ type: 'spring', stiffness: 50, damping: 20 }}
                                        style={{ height: '100%', background: 'var(--gradient-primary)', borderRadius: 4, boxShadow: '0 0 10px var(--color-primary-glow)' }}
                                    />
                                </div>
                                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, fontWeight: 600 }}>
                                    <span style={{ color: 'var(--color-primary-light)' }}>{progress}% Optimized</span>
                                    <motion.span 
                                        animate={{ opacity: [1, 0.5, 1] }}
                                        transition={{ duration: 1.5, repeat: Infinity }}
                                        style={{ color: 'var(--color-text-dim)' }}
                                    >
                                        Analyzing patterns...
                                    </motion.span>
                                </div>
                            </div>
                        )}

                        {progress === undefined && (
                            <motion.div 
                                animate={{ opacity: [0.4, 1, 0.4] }}
                                transition={{ duration: 2, repeat: Infinity }}
                                style={{ fontSize: 13, color: 'var(--color-primary-light)', fontWeight: 600 }}
                            >
                                Running neural matching algorithms...
                            </motion.div>
                        )}
                    </motion.div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}
