import { promises as fs } from 'node:fs';
import { URL } from 'node:url';

type Region = "de" | "uk" | "ny" | "la" | "sg" | "se" | "br" | "jh" | "syd";

class Storage {
    private apiKey: string;
    private zone: string;
    private region: Region;

    constructor(apiKey: string, zone: string, region: Region = "de") {
        this.apiKey = apiKey;
        this.zone = zone;
        this.region = region;
    }

    public getContentType(filepath: string): string {
        if (filepath.endsWith('.gif')) {
            return 'image/gif';
        } else if (filepath.endsWith('.png')) {
            return 'image/png';
        } else if (filepath.endsWith('.jpg') || filepath.endsWith('.jpeg')) {
            return 'image/jpeg';
        } else if (filepath.endsWith('.mp4')) {
            return 'video/mp4';
        } else {
            throw new Error(`There is no handled content type for extension ${filepath.split('.').pop()}`);
        }
    }

    private get baseUrl(): string {
        return this.region === "de"
            ? `https://storage.bunnycdn.com/${this.zone}/`
            : `https://${this.region}.storage.bunnycdn.com/${this.zone}/`;
    }

    private get headers(): Record<string, string> {
        return { "AccessKey": this.apiKey };
    }

    private getUrl(storagePath?: string, deletePath?: string): string {
        if (storagePath) {
            if (storagePath.startsWith('/')) {
                storagePath = storagePath.slice(1);
            }
            if (storagePath.endsWith('/')) {
                storagePath = storagePath.slice(0, -1);
            }
            // Remove encodeURIComponent to prevent encoding slashes
            return new URL(storagePath, this.baseUrl).toString();
        } else if (deletePath) {
            if (deletePath.endsWith('/')) {
                deletePath = deletePath.slice(0, -1);
            }
            // Remove encodeURIComponent to prevent encoding slashes
            return new URL(deletePath, this.baseUrl).toString();
        }
        throw new Error("Either storagePath or deletePath must be provided.");
    }

    private async readFile(filepath: string): Promise<Buffer> {
        return fs.readFile(filepath);
    }

    public async upload(uploadPath: string, filepath?: string, file?: Buffer): Promise<{ success: boolean; url: string }> {
        let data: Buffer;
        if (filepath) {
            data = await this.readFile(filepath);
        } else if (file) {
            data = file;
        } else {
            throw new Error("You must provide either a filepath or file argument");
        }

        const response = await fetch(this.getUrl(uploadPath), {
            method: 'PUT',
            headers: {
                ...this.headers,
                'Content-Type': this.getContentType(uploadPath),
            },
            body: data,
        });

        if (!response.ok) {
            throw new Error(`Failed to upload file ${response.status}: ${await response.text()}`);
        }

        return { success: true, url: response.url };
    }

    public async get(path: string): Promise<Buffer> {
        const url = this.getUrl(path);
        console.log(url);
        const response = await fetch(url, { headers: this.headers });

        if (!response.ok) {
            throw new Error(`Request for url ${url} failed with status ${response.status}`);
        }

        return await response.arrayBuffer().then(buffer => new Uint8Array(buffer));
    }

    public async list(path?: string): Promise<any> {
        const url = path ? this.getUrl(path) : this.baseUrl;
        const response = await fetch(url, { headers: this.headers });

        if (!response.ok) {
            throw new Error(`Failed to list files at ${url} with status ${response.status}`);
        }

        return await response.json();
    }

    public async delete(path: string): Promise<boolean> {
        const url = this.getUrl(undefined, path);
        const response = await fetch(url, {
            method: 'DELETE',
            headers: this.headers,
        });

        if (!response.ok) {
            throw new Error(`Deleting file at ${url} failed with status ${response.status}`);
        }

        return true;
    }
}

export default Storage;