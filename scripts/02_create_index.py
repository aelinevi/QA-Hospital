#!/usr/bin/env python3
"""
Script 2: Create OpenSearch Index dengan Mapping
Rumah Sakit Sehat Selalu - QA System
"""

import requests
import json

OPENSEARCH_URL = "http://localhost:9200"
INDEX_NAME = "hospital_registrations"

# Delete index if exists
requests.delete(f"{OPENSEARCH_URL}/{INDEX_NAME}")

# Create index with mapping
mapping = {
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
        "analysis": {
            "analyzer": {
                "indonesian_analyzer": {
                    "type": "standard",
                    "stopwords": "_indonesian_"
                }
            }
        }
    },
    "mappings": {
        "properties": {
            "id_registrasi": {"type": "keyword"},
            "tanggal_registrasi": {"type": "date"},
            "id_pasien": {"type": "keyword"},
            "nama_pasien": {
                "type": "text",
                "analyzer": "indonesian_analyzer",
                "fields": {"keyword": {"type": "keyword"}}
            },
            "is_vip": {"type": "boolean"},
            "metode_pembayaran_awal": {"type": "keyword"},
            "nama_tim": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword"}}
            },
            "deskripsi_tim": {"type": "text"},
            "dokter_terlibat": {
                "type": "nested",
                "properties": {
                    "nama": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword"}}
                    },
                    "departemen": {"type": "keyword"}
                }
            },
            "id_billing": {"type": "keyword"},
            "status_pembayaran": {"type": "keyword"},
            "total_biaya": {"type": "long"},
            "rincian_layanan": {
                "type": "nested",
                "properties": {
                    "nama_layanan": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword"}}
                    },
                    "biaya_satuan": {"type": "long"},
                    "dokter_pelaksana": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword"}}
                    },
                    "is_covered_asuransi": {"type": "boolean"}
                }
            },
            "nomor_polis": {"type": "keyword"},
            "jumlah_cover_asuransi": {"type": "long"},
            # Full-text search field (combined)
            "text_untuk_search": {
                "type": "text",
                "analyzer": "indonesian_analyzer"
            }
        }
    }
}

response = requests.put(
    f"{OPENSEARCH_URL}/{INDEX_NAME}",
    headers={"Content-Type": "application/json"},
    data=json.dumps(mapping)
)
print(f"Create index: {response.status_code}")
print(json.dumps(response.json(), indent=2))
