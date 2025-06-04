use actix_web::{get, App, HttpServer, Responder, HttpResponse};
use rand::seq::SliceRandom;
use rand::prelude::IteratorRandom;
use std::fs;
use std::collections::HashMap;
use std::sync::RwLock;
use std::time::{SystemTime, UNIX_EPOCH};
use sha2::{Sha256, Digest};
use actix_web::web::Data;
use std::path::{Path, PathBuf};

const VALID_TOKEN: &str = "";

struct HashStore {
    mappings: HashMap<String, (String, u64)>,
}

impl HashStore {
    fn new() -> Self {
        Self {
            mappings: HashMap::new(),
        }
    }

    fn generate_hash(path: &str) -> String {
        let mut hasher = Sha256::new();
        hasher.update(format!("{}{}", path, SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_nanos()));
        let result = hasher.finalize();
        hex::encode(&result[..4]) 
    }

    fn add_mapping(&mut self, real_path: String) -> String {
        let now = SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_secs();
        self.mappings.retain(|_, (_, exp)| *exp > now);

        let hash = Self::generate_hash(&real_path);
        println!("Adding mapping: {} -> {}", hash, real_path);
        self.mappings.insert(hash.clone(), (real_path, now + 3600));
        hash
    }

    fn get_real_path(&self, hash: &str) -> Option<String> {
        let now = SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_secs();
        self.mappings.get(hash).and_then(|(path, exp)| {
            if *exp > now {
                Some(path.clone())
            } else {
                None
            }
        })
    }
}

struct CachedCategory {
    files: Vec<(String, String)>, 
    last_update: SystemTime,
}

struct FileCache {
    categories: HashMap<String, CachedCategory>,
}

impl FileCache {
    fn new() -> Self {
        Self {
            categories: HashMap::new(),
        }
    }

    fn get_or_update_category(&mut self, category_path: &Path) -> Option<&CachedCategory> {
        let category_name = category_path.file_name()?.to_string_lossy().to_string();
        
        let should_update = self.categories
            .get(&category_name)
            .map(|cat| cat.last_update.elapsed().unwrap().as_secs() > 300)
            .unwrap_or(true);

        if should_update {
            let mut files = Vec::new();
            if let Ok(entries) = fs::read_dir(category_path) {
                for entry in entries.filter_map(Result::ok) {
                    if let Ok(metadata) = entry.metadata() {
                        if !metadata.is_dir() && metadata.len() > 0 {
                            let filename = entry.file_name().to_string_lossy().to_string();
                            let format_type = Path::new(&filename)
                                .extension()
                                .and_then(|ext| ext.to_str())
                                .unwrap_or("unknown")
                                .to_lowercase();
                            files.push((filename, format_type));
                        }
                    }
                }
            }
            
            if !files.is_empty() {
                self.categories.insert(category_name.clone(), CachedCategory {
                    files,
                    last_update: SystemTime::now(),
                });
            }
        }

        self.categories.get(&category_name)
    }
}

struct AppState {
    hash_store: HashStore,
    file_cache: FileCache,
}

fn get_random_file(base_dir: &Path, category: Option<&str>, app_state: &RwLock<AppState>) -> Option<(String, String, String)> {
    let mut rng = rand::thread_rng();
    let mut state = app_state.write().unwrap();
    
    let categories = fs::read_dir(base_dir).ok()?
        .filter_map(Result::ok)
        .filter(|entry| entry.metadata().map(|m| m.is_dir()).unwrap_or(false))
        .collect::<Vec<_>>();

    if categories.is_empty() {
        return None;
    }

    let target_category = if let Some(cat) = category {
        categories.iter()
            .find(|entry| entry.file_name().to_string_lossy() == cat)?
            .path()
    } else {
        categories.choose(&mut rng)?.path()
    };

    let category_name = target_category.file_name()?.to_string_lossy().to_string();
    let cached_category = state.file_cache.get_or_update_category(&target_category)?;
    
    if let Some((filename, format_type)) = cached_category.files.choose(&mut rng) {
        Some((filename.clone(), format_type.clone(), category_name))
    } else {
        None
    }
}

#[get("/random/{type}/{category}")]
async fn random_file_category(
    path: actix_web::web::Path<(String, String)>,
    req: actix_web::HttpRequest,
    app_state: Data<RwLock<AppState>>
) -> impl Responder {
    let token = req.query_string()
        .split('&')
        .find(|&pair| pair.starts_with("token="))
        .and_then(|pair| pair.split('=').nth(1));

    if token != Some(VALID_TOKEN) {
        return HttpResponse::Unauthorized().body("Invalid or missing token");
    }

    let (file_type, category) = path.into_inner();
    let base_path = std::env::current_dir().unwrap();
    
    let base_dir = match file_type.as_str() {
        "pfps" => base_path.join("cdn_files").join("avatars"),
        "banners" => base_path.join("cdn_files").join("banners"),
        _ => return HttpResponse::NotFound().json(serde_json::json!({
            "error": "Invalid type. Use 'pfps' or 'banners'"
        }))
    };

    if let Some((filename, format_type, category_name)) = get_random_file(&base_dir, Some(&category), app_state.as_ref()) {
        let real_path = format!("/cdn_files/{}/{}/{}", 
            if file_type == "pfps" { "avatars" } else { "banners" },
            category_name,
            filename
        );
        
        let hash = app_state.write().unwrap().hash_store.add_mapping(real_path);
        let hashed_url = format!("/cdn_files/{}.{}", hash, format_type);
        
        return HttpResponse::Ok().json(serde_json::json!({
            "url": format!("https://cdn.evict.bot{}", hashed_url),
            "filename": filename,
            "format_type": format_type,
            "category": category_name
        }));
    }

    HttpResponse::NotFound().json(serde_json::json!({
        "error": "No files found in category"
    }))
}

#[get("/random/{type}")]
async fn random_file_type(
    path: actix_web::web::Path<String>,
    req: actix_web::HttpRequest,
    app_state: Data<RwLock<AppState>>
) -> impl Responder {
    let token = req.query_string()
        .split('&')
        .find(|&pair| pair.starts_with("token="))
        .and_then(|pair| pair.split('=').nth(1));

    if token != Some(VALID_TOKEN) {
        return HttpResponse::Unauthorized().body("Invalid or missing token");
    }

    let file_type = path.into_inner();
    let base_path = std::env::current_dir().unwrap();
    
    let base_dir = match file_type.as_str() {
        "pfps" => base_path.join("cdn_files").join("avatars"),
        "banners" => base_path.join("cdn_files").join("banners"),
        _ => return HttpResponse::NotFound().json(serde_json::json!({
            "error": "Invalid type. Use 'pfps' or 'banners'"
        }))
    };

    if let Some((filename, format_type, category_name)) = get_random_file(&base_dir, None, app_state.as_ref()) {
        let real_path = format!("/cdn_files/{}/{}/{}", 
            if file_type == "pfps" { "avatars" } else { "banners" },
            category_name,
            filename
        );
        
        let hash = app_state.write().unwrap().hash_store.add_mapping(real_path);
        let hashed_url = format!("/cdn_files/{}.{}", hash, format_type);
        
        return HttpResponse::Ok().json(serde_json::json!({
            "url": format!("https://cdn.evict.bot{}", hashed_url),
            "filename": filename,
            "format_type": format_type,
            "category": category_name
        }));
    }

    HttpResponse::NotFound().json(serde_json::json!({
        "error": "No files found"
    }))
}

#[get("/cdn_files/{hash_path}")]
async fn serve_file(
    path: actix_web::web::Path<String>,
    app_state: Data<RwLock<AppState>>
) -> Result<actix_web::HttpResponse, actix_web::Error> {
    let hash_path = path.into_inner();
    let hash = hash_path.split('.').next().unwrap_or("");
    
    println!("Attempting to serve file with hash: {}", hash);
    
    if let Some(real_path) = app_state.read().unwrap().hash_store.get_real_path(hash) {
        println!("Found real path: {}", real_path);
        let base_path = std::env::current_dir().unwrap();
        let file_path = base_path.join(&real_path[1..]);
        
        println!("Full file path: {:?}", file_path);
        
        if file_path.exists() {
            println!("File exists, attempting to read");
            match fs::read(&file_path) {
                Ok(content) => {
                    println!("File read successfully, size: {} bytes", content.len());
                    let content_type = match file_path.extension()
                        .and_then(|ext| ext.to_str())
                        .map(|ext| ext.to_lowercase())
                    {
                        Some(ext) => match ext.as_str() {
                            "jpg" | "jpeg" => "image/jpeg",
                            "png" => "image/png",
                            "gif" => "image/gif",
                            "webp" => "image/webp",
                            _ => "application/octet-stream",
                        },
                        None => "application/octet-stream",
                    };
                    println!("Serving with content-type: {}", content_type);

                    Ok(HttpResponse::Ok()
                        .content_type(content_type)
                        .body(content))
                },
                Err(e) => {
                    println!("Error reading file: {:?}", e);
                    Err(actix_web::error::ErrorInternalServerError("Failed to read file"))
                }
            }
        } else {
            println!("File does not exist: {:?}", file_path);
            Err(actix_web::error::ErrorNotFound("File not found"))
        }
    } else {
        println!("No mapping found for hash: {}", hash);
        Err(actix_web::error::ErrorNotFound("Invalid hash"))
    }
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    let base_path = std::env::current_dir()?;
    let cdn_path = base_path.join("cdn_files");
    
    println!("Starting server...");
    println!("Current directory: {:?}", base_path);
    println!("CDN directory: {:?}", cdn_path);
    
    if !cdn_path.exists() {
        println!("Warning: CDN directory does not exist!");
        fs::create_dir_all(&cdn_path)?;
        println!("Created CDN directory");
    }

    let app_state = Data::new(RwLock::new(AppState {
        hash_store: HashStore::new(),
        file_cache: FileCache::new(),
    }));
    
    HttpServer::new(move || {
        App::new()
            .app_data(app_state.clone())
            .service(random_file_category)
            .service(random_file_type)
            .service(serve_file)
    })
    .bind(("127.0.0.1", 8080))?
    .run()
    .await
}