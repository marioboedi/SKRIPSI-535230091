# Reproduksi eksperimen PROMPT 02

Versi analisis **1.1.0** memperbaiki cakupan standardisasi tanpa mengganti parameter model atau aturan pemilihan K. Pada dataset bawaan `2425.csv`, seluruh **81 nilai evaluasi** dalam PROMPT 02 dapat direproduksi pada pembulatan empat desimal.

## Penyebab perbedaan

Versi sebelumnya menghitung satu rata-rata dan simpangan baku per indikator dengan menggabungkan observasi 2024 dan 2025. Tabel eksperimen dapat direproduksi dengan menghitung **Z-score secara terpisah per tahun**, sebelum rata-rata antarperiode.

Urutan yang digunakan:

1. Pisahkan observasi berdasarkan `tahun`.
2. Jalankan `StandardScaler` pada sembilan indikator setiap tahun, memakai simpangan baku populasi (`ddof=0`).
3. Gabungkan kembali observasi yang sudah distandardisasi, dengan identitas wilayah tetap sejajar.
4. Ambil rata-rata Z-score berdasarkan `kota`, `kecamatan`, dan `kelurahan`.
5. Urutkan hasil menurut ketiga kolom tersebut. Urutan baris penting untuk inisialisasi algoritma dengan random state.
6. Uji K=2–10 dan pilih K melalui mayoritas metrik seperti semula.

## Hasil pada dataset bawaan

| Algoritma | K optimal | Silhouette ↑ | DBI ↓ | CHI ↑ | Dukungan pemilihan K |
| --- | ---: | ---: | ---: | ---: | --- |
| K-Means | 3 | 0,3500 | 0,9426 | 107,8559 | DBI dan CHI |
| AHC Ward | 3 | 0,2495 | 1,0020 | 94,9169 | Ketiga metrik |
| Spectral Bridges | 2 | 0,6455 | 1,3079 | 38,2610 | Silhouette dan DBI |

Hasil di atas dihitung dari data asli. K dan skor referensi tidak digunakan sebagai nilai pengganti dalam aplikasi. CSV unggahan tetap dihitung dari isinya sendiri dan dapat menghasilkan K optimal berbeda.

Referensi sembilan kandidat K per metode disimpan sebagai fixture pengujian pada `tests/fixtures/prompt02_*.csv`. Setiap metode memiliki 27 perbandingan angka: sembilan kandidat × tiga metrik. Tes memakai toleransi 0,000050001 karena nilai referensi dibulatkan menjadi empat desimal; durasi proses tidak dibandingkan karena bergantung pada perangkat.

Cache analisis menggunakan versi `1.1.0` secara eksplisit agar hasil versi lama tidak digunakan kembali. Teks metodologi pada aplikasi, FAQ, dokumentasi, dan metadata laporan ZIP telah disesuaikan ke standardisasi per tahun.
