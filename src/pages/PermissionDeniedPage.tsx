import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { AlertTriangle } from 'lucide-react';

export default function PermissionDeniedPage() {
    return (
        <div className="flex flex-col items-center justify-center h-screen bg-background text-foreground">
            <div className="text-center p-8 bg-card rounded-lg shadow-lg">
                <AlertTriangle className="w-16 h-16 text-destructive mx-auto mb-4" />
                <h1 className="text-4xl font-bold mb-2">访问被拒绝</h1>
                <p className="text-muted-foreground mb-6">抱歉，您没有权限访问此页面。</p>
                <Button asChild>
                    <Link to="/dashboard">返回仪表盘</Link>
                </Button>
            </div>
        </div>
    );
}