// 导出/导入工具函数

/**
 * 导出数据为JSON文件
 * @param data - 要导出的数据
 * @param filename - 文件名（不含扩展名）
 */
export function exportToJSON<T>(data: T, filename: string): void {
    const json = JSON.stringify(data, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);

    const link = document.createElement('a');
    link.href = url;
    link.download = `${filename}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
}

/**
 * 从JSON文件导入数据
 * @returns Promise包含解析后的数据
 */
export function importFromJSON<T>(returnAsText?: boolean): Promise<T | string> {
    return new Promise((resolve, reject) => {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '.json';

        input.onchange = async (e) => {
            const file = (e.target as HTMLInputElement).files?.[0];
            if (!file) {
                reject(new Error('未选择文件'));
                return;
            }

            try {
                const text = await file.text();
                if (returnAsText) {
                    resolve(text);
                } else {
                    const data = JSON.parse(text);
                    resolve(data as T);
                }
            } catch (error) {
                reject(new Error('文件解析失败'));
            }
        };

        input.click();
    });
}

/**
 * 批量导出数据为JSON文件
 * @param items - 要导出的数据数组
 * @param filename - 文件名前缀
 */
export function exportMultipleToJSON<T>(items: T[], filename: string): void {
    exportToJSON(items, `${filename}-export-${Date.now()}`);
}
