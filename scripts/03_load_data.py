#!/usr/bin/env python3
"""
Script 3: Transform & Load Data ke OpenSearch
Rumah Sakit Sehat Selalu - QA System

Transformasi dari format key-value JSON ke dokumen OpenSearch yang flat
dan full-text searchable.
"""

import json
import requests
from datetime import datetime

OPENSEARCH_URL = "http://localhost:9200"
INDEX_NAME = "hospital_registrations"
DATA_FILE = "key_value_data_1000.json"

def transform_record(record):
    """
    Transformasi satu record dari format key-value ke dokumen OpenSearch.
    """
    key = record["key"]  # contoh: "registrasi:REG-20230905-001"
    val = record["value"]

    id_registrasi = key.split(":", 1)[1] if ":" in key else key

    pasien = val.get("pasien") or {}
    tim = val.get("tim_medis") or {}
    billing = val.get("billing") or {}
    klaim = billing.get("klaim_asuransi") or {}
    rincian = billing.get("rincian_layanan") or []
    dokter_list = tim.get("dokter_terlibat") or []

    # Buat teks gabungan untuk full-text search
    dokter_names = ", ".join([d.get("nama", "") for d in dokter_list])
    layanan_names = ", ".join([l.get("nama_layanan", "") for l in rincian])
    
    text_search = " ".join(filter(None, [
        id_registrasi,
        pasien.get("nama_pasien", ""),
        pasien.get("id_pasien", ""),
        val.get("metode_pembayaran_awal", ""),
        tim.get("nama_tim", ""),
        tim.get("deskripsi", ""),
        dokter_names,
        layanan_names,
        billing.get("status_pembayaran", ""),
        klaim.get("nomor_polis", ""),
        "VIP" if pasien.get("is_vip") else "",
        "BPJS" if val.get("metode_pembayaran_awal") == "BPJS" else "",
    ]))

    doc = {
        "id_registrasi": id_registrasi,
        "tanggal_registrasi": val.get("tanggal_registrasi"),
        "id_pasien": pasien.get("id_pasien"),
        "nama_pasien": pasien.get("nama_pasien"),
        "is_vip": pasien.get("is_vip", False),
        "metode_pembayaran_awal": val.get("metode_pembayaran_awal"),
        "nama_tim": tim.get("nama_tim"),
        "deskripsi_tim": tim.get("deskripsi"),
        "dokter_terlibat": dokter_list,
        "id_billing": billing.get("id_billing"),
        "status_pembayaran": billing.get("status_pembayaran"),
        "total_biaya": billing.get("total_biaya", 0),
        "rincian_layanan": rincian,
        "nomor_polis": klaim.get("nomor_polis"),
        "jumlah_cover_asuransi": klaim.get("jumlah_cover", 0),
        "text_untuk_search": text_search
    }
    return id_registrasi, doc


def bulk_load(records, batch_size=100):
    """Load data ke OpenSearch menggunakan Bulk API."""
    total = len(records)
    loaded = 0
    errors = 0

    for i in range(0, total, batch_size):
        batch = records[i:i + batch_size]
        bulk_body = ""

        for record in batch:
            try:
                doc_id, doc = transform_record(record)
                action = json.dumps({"index": {"_index": INDEX_NAME, "_id": doc_id}})
                source = json.dumps(doc, ensure_ascii=False)
                bulk_body += action + "\n" + source + "\n"
            except Exception as e:
                print(f"Error transforming {record.get('key')}: {e}")
                errors += 1

        if bulk_body:
            response = requests.post(
                f"{OPENSEARCH_URL}/_bulk",
                headers={"Content-Type": "application/x-ndjson"},
                data=bulk_body.encode("utf-8")
            )
            result = response.json()
            if result.get("errors"):
                for item in result.get("items", []):
                    idx = item.get("index", {})
                    if idx.get("error"):
                        print(f"  Bulk error: {idx['error']}")
                        errors += 1
            loaded += len(batch)
            print(f"  Loaded {loaded}/{total} records...")

    return loaded, errors


if __name__ == "__main__":
    print(f"=== Loading data ke OpenSearch: {INDEX_NAME} ===")
    print(f"Membaca file: {DATA_FILE}")

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        records = json.load(f)

    print(f"Total records: {len(records)}")
    start = datetime.now()

    loaded, errors = bulk_load(records)

    elapsed = (datetime.now() - start).total_seconds()
    print(f"\n=== Selesai ===")
    print(f"Loaded  : {loaded} dokumen")
    print(f"Errors  : {errors}")
    print(f"Waktu   : {elapsed:.1f} detik")

    # Verify count
    count_resp = requests.get(f"{OPENSEARCH_URL}/{INDEX_NAME}/_count")
    print(f"Dokumen di OpenSearch: {count_resp.json().get('count')}")