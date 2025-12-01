import { useState, useRef, useLayoutEffect } from 'react';
import { Eye, EyeOff } from 'lucide-react';

interface MaskedKeyProps {
  apiKey: string;
}

export default function MaskedKey({ apiKey }: MaskedKeyProps) {
  const [isHovered, setIsHovered] = useState(false);
  const [width, setWidth] = useState(0);
  const codeRef = useRef<HTMLElement>(null);

  useLayoutEffect(() => {
    // We render the actual key once off-screen to measure its width.
    const tempElement = document.createElement('code');
    tempElement.className = "relative rounded bg-muted px-[0.3rem] py-[0.2rem] font-mono text-sm break-all";
    tempElement.style.position = 'absolute';
    tempElement.style.visibility = 'hidden';
    tempElement.style.whiteSpace = 'nowrap';
    tempElement.innerText = apiKey;
    document.body.appendChild(tempElement);
    setWidth(tempElement.offsetWidth);
    document.body.removeChild(tempElement);
  }, [apiKey]);

  return (
    <div
      className="flex items-center gap-2"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <code
        ref={codeRef}
        className="relative rounded bg-muted px-[0.3rem] py-[0.2rem] font-mono text-sm break-all"
        title={apiKey}
        style={{ minWidth: `${width}px`, display: 'inline-block', textAlign: 'center' }}
      >
        {isHovered ? apiKey : '∗'.repeat(apiKey.length)}
      </code>
      {isHovered ? <EyeOff className="w-3 h-3" /> : <Eye className="w-3 h-3" />}
    </div>
  );
}