const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface SolutionStep {
    step_number: number;
    description: string;
    formula?: string;
    result?: string;
}

export interface SolveResponse {
    id: string;
    status: string;
    problem: {
        text: string;
        type: string;
    };
    solution: {
        steps: SolutionStep[];
        answer: string;
    };
    visualization: {
        static_image?: string;
        animation_gif?: string;
        video_mp4?: string;
    };
    metadata: {
        model: string;
        processing_time_ms: number;
    };
    geometry_dsl?: string;
}

export async function solveWithImage(file: File): Promise<SolveResponse> {
    const formData = new FormData();
    formData.append('image', file);

    const response = await fetch(`${API_BASE_URL}/api/v1/solve`, {
        method: 'POST',
        body: formData,
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(error.detail || 'Failed to solve problem');
    }

    return response.json();
}

export async function solveWithText(text: string): Promise<SolveResponse> {
    const formData = new FormData();
    formData.append('text', text);

    const response = await fetch(`${API_BASE_URL}/api/v1/solve`, {
        method: 'POST',
        body: formData,
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(error.detail || 'Failed to solve problem');
    }

    return response.json();
}

export async function checkHealth(): Promise<{ status: string; environment: string }> {
    const response = await fetch(`${API_BASE_URL}/api/health`);
    return response.json();
}
