'use client';

import React from 'react';

interface Step {
    step_number: number;
    description: string;
    formula?: string;
    result?: string;
}

interface Solution {
    steps: Step[];
    answer: string;
}

interface Problem {
    text: string;
    type: string;
}

interface SolutionDisplayProps {
    problem: Problem;
    solution: Solution;
    geometryDsl?: string;
}

export default function SolutionDisplay({ problem, solution, geometryDsl }: SolutionDisplayProps) {
    const getProblemTypeLabel = (type: string) => {
        const labels: Record<string, string> = {
            'algebra': '📐 Đại số',
            'geometry_2d': '📏 Hình học phẳng',
            'geometry_3d': '🎲 Hình học không gian',
            'oxyz': '📊 Hình học Oxyz',
            'unknown': '📝 Bài toán',
        };
        return labels[type] || labels['unknown'];
    };

    return (
        <div className="w-full max-w-3xl mx-auto animate-fade-in">
            {/* Problem Section */}
            <div className="glass-card p-6 mb-6">
                <div className="flex items-center gap-3 mb-4">
                    <span className="text-2xl">{getProblemTypeLabel(problem.type).split(' ')[0]}</span>
                    <h2 className="text-xl font-bold gradient-text">
                        {getProblemTypeLabel(problem.type).split(' ').slice(1).join(' ')}
                    </h2>
                </div>
                <p className="text-gray-300 leading-relaxed">{problem.text}</p>
            </div>

            {/* Solution Steps */}
            <div className="mb-6">
                <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                    <span className="text-primary">📝</span>
                    Lời giải chi tiết
                </h3>

                <div className="space-y-4">
                    {solution.steps.map((step, index) => (
                        <div
                            key={index}
                            className="step-card animate-fade-in"
                            style={{ animationDelay: `${index * 0.1}s` }}
                        >
                            <div className="flex items-start gap-4">
                                <span className="step-number flex-shrink-0">
                                    {step.step_number}
                                </span>
                                <div className="flex-1">
                                    <p className="text-gray-200 mb-2">{step.description}</p>

                                    {step.formula && (
                                        <div className="latex-formula my-3">
                                            <code className="text-secondary">{step.formula}</code>
                                        </div>
                                    )}

                                    {step.result && (
                                        <p className="text-primary-light font-medium">
                                            → {step.result}
                                        </p>
                                    )}
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Final Answer */}
            <div className="answer-highlight animate-fade-in" style={{ animationDelay: '0.5s' }}>
                <div className="flex items-center gap-3 mb-2">
                    <span className="text-2xl">✅</span>
                    <h3 className="text-lg font-semibold text-success">Đáp án</h3>
                </div>
                <p className="text-xl font-medium text-white">{solution.answer}</p>
            </div>

            {/* Geometry DSL (Debug) */}
            {geometryDsl && (
                <details className="mt-6">
                    <summary className="text-gray-500 cursor-pointer hover:text-gray-300 transition-colors">
                        🔧 Geometry DSL (Developer)
                    </summary>
                    <pre className="mt-2 p-4 bg-surface rounded-lg text-sm text-gray-400 overflow-x-auto">
                        {geometryDsl}
                    </pre>
                </details>
            )}
        </div>
    );
}
