#!/usr/bin/env python3
"""
Script 4: QA Backend API (FastAPI) - menggunakan Google Gemini (GRATIS)
Rumah Sakit Sehat Selalu - QA System

Endpoint:
  POST /api/ask   - Terima pertanyaan, cari di OpenSearch, jawab dengan Gemini
  GET  /api/search - Cari langsung di OpenSearch
  GET  /api/stats  - Statistik data
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import json
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Hospital QA System", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

OPENSEARCH_URL = os.getenv("OPENSEARCH_URL", "http://localhost:9200")
INDEX_NAME = "hospital_registrations"

# Setup Gemini
api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-2.5-flash")  # model gratis


class QuestionRequest(BaseModel):
    question: str


def search_opensearch(query: str, size: int = 5) -> list:
    """Cari dokumen relevan di OpenSearch."""
    body = {
        "size": size,
        "query": {
            "bool": {
                "should": [
                    {
                        "match": {
                            "text_untuk_search": {
                                "query": query,
                                "fuzziness": "AUTO"
                            }
                        }
                    },
                    {
                        "match": {
                            "nama_pasien": {"query": query, "boost": 2}
                        }
                    },
                    {
                        "match": {
                            "nama_tim": {"query": query, "boost": 1.5}
                        }
                    },
                    {
                        "nested": {
                            "path": "dokter_terlibat",
                            "query": {
                                "match": {
                                    "dokter_terlibat.nama": {"query": query, "boost": 2}
                                }
                            }
                        }
                    },
                    {
                        "nested": {
                            "path": "rincian_layanan",
                            "query": {
                                "match": {
                                    "rincian_layanan.nama_layanan": {"query": query}
                                }
                            }
                        }
                    },
                    {"term": {"id_registrasi": query}},
                    {"term": {"id_pasien": query}}
                ]
            }
        },
        "_source": {"excludes": ["text_untuk_search"]}
    }

    resp = requests.post(
        f"{OPENSEARCH_URL}/{INDEX_NAME}/_search",
        headers={"Content-Type": "application/json"},
        data=json.dumps(body)
    )
    hits = resp.json().get("hits", {}).get("hits", [])
    return [h["_source"] for h in hits]


def format_docs_for_context(docs: list) -> str:
    """Format dokumen OpenSearch menjadi konteks teks untuk Gemini."""
    if not docs:
        return "Tidak ditemukan data yang relevan."

    parts = []
    for i, doc in enumerate(docs, 1):
        layanan = ", ".join([l["nama_layanan"] for l in doc.get("rincian_layanan", [])])
        dokter = ", ".join([d["nama"] for d in doc.get("dokter_terlibat", [])])
        parts.append(f"""
[Data {i}]
ID Registrasi  : {doc.get('id_registrasi')}
Tanggal        : {doc.get('tanggal_registrasi', '')[:10]}
Pasien         : {doc.get('nama_pasien')} ({doc.get('id_pasien')}) {'[VIP]' if doc.get('is_vip') else ''}
Pembayaran     : {doc.get('metode_pembayaran_awal')}
Tim Medis      : {doc.get('nama_tim')} — {doc.get('deskripsi_tim')}
Dokter         : {dokter}
Layanan        : {layanan}
Total Biaya    : Rp {doc.get('total_biaya', 0):,}
Status Bayar   : {doc.get('status_pembayaran')}
Nomor Polis    : {doc.get('nomor_polis', '-')}
Cover Asuransi : Rp {doc.get('jumlah_cover_asuransi', 0):,}
""")
    return "\n".join(parts)


@app.post("/api/ask")
async def ask_question(req: QuestionRequest):
    """Endpoint utama QA: cari konteks di OpenSearch, lalu jawab dengan Gemini."""
    question = req.question.strip()
    if not question:
        raise HTTPException(400, "Pertanyaan tidak boleh kosong")

    # 1. Cari dokumen relevan di OpenSearch
    docs = search_opensearch(question, size=5)
    context = format_docs_for_context(docs)

    # 2. Kirim ke Gemini untuk dijawab
    prompt = f"""Kamu adalah asisten QA untuk sistem informasi Rumah Sakit Sehat Selalu.
Jawab pertanyaan berdasarkan data registrasi pasien berikut.
Jawab dengan bahasa Indonesia yang jelas dan informatif.
Jika data tidak cukup untuk menjawab, katakan dengan jujur.
Format angka mata uang dengan Rp dan pemisah ribuan.

Konteks data dari database rumah sakit:
{context}

Pertanyaan: {question}"""

    response = model.generate_content(prompt)
    answer = response.text

    return {
        "question": question,
        "answer": answer,
        "sources": docs,
        "total_sources": len(docs)
    }


@app.get("/api/search")
async def search(q: str, size: int = 10):
    """Cari langsung di OpenSearch."""
    if not q:
        raise HTTPException(400, "Parameter q diperlukan")
    docs = search_opensearch(q, size=size)
    return {"query": q, "results": docs, "total": len(docs)}


@app.get("/api/stats")
async def get_stats():
    """Statistik data rumah sakit di OpenSearch."""
    body = {
        "size": 0,
        "aggs": {
            "total_pasien": {"cardinality": {"field": "id_pasien"}},
            "metode_pembayaran": {"terms": {"field": "metode_pembayaran_awal"}},
            "status_pembayaran": {"terms": {"field": "status_pembayaran"}},
            "total_pendapatan": {"sum": {"field": "total_biaya"}},
            "pasien_vip": {"filter": {"term": {"is_vip": True}}},
            "per_tim": {"terms": {"field": "nama_tim.keyword", "size": 20}}
        }
    }
    resp = requests.post(
        f"{OPENSEARCH_URL}/{INDEX_NAME}/_search",
        headers={"Content-Type": "application/json"},
        data=json.dumps(body)
    )
    result = resp.json()
    aggs = result.get("aggregations", {})
    count_resp = requests.get(f"{OPENSEARCH_URL}/{INDEX_NAME}/_count")

    return {
        "total_registrasi": count_resp.json().get("count"),
        "total_pasien_unik": aggs.get("total_pasien", {}).get("value"),
        "total_pendapatan": aggs.get("total_pendapatan", {}).get("value"),
        "pasien_vip": aggs.get("pasien_vip", {}).get("doc_count"),
        "metode_pembayaran": {
            b["key"]: b["doc_count"]
            for b in aggs.get("metode_pembayaran", {}).get("buckets", [])
        },
        "status_pembayaran": {
            b["key"]: b["doc_count"]
            for b in aggs.get("status_pembayaran", {}).get("buckets", [])
        },
        "per_tim": {
            b["key"]: b["doc_count"]
            for b in aggs.get("per_tim", {}).get("buckets", [])
        }
    }


@app.get("/")
async def root():
    return {"message": "Hospital QA System API - Powered by Gemini", "docs": "/docs"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
