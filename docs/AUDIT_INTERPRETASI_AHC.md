# Audit interpretasi profil AHC — aplikasi 1.3.1

Label Risiko Rendah yang sama berasal dari aturan kategori penelitian, bukan kesalahan pemetaan nomor atau pemakaian ulang profil. Kategori tersebut ditetapkan bila rata-rata centroid empat indikator listrik dan lima indikator gas masing-masing tidak melampaui 0,5. Aturan ini merangkum banyak pola berbeda ke satu kategori, sehingga kategori saja belum menjelaskan karakteristik tiap klaster.

## Hasil audit data bawaan

| Klaster | Kelurahan | Proporsi | Indeks listrik | Indeks gas | Kategori asli | Karakteristik centroid |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| 1 | 1 | 0,4% | −1,129682 | 6,403193 | Dominan Bahaya Gas | 4 dari 9 di atas acuan tahunan, 5 di bawah |
| 2 | 128 | 47,9% | 0,338336 | 0,433517 | Risiko Rendah | 9 dari 9 di atas acuan tahunan |
| 3 | 138 | 51,7% | −0,305633 | −0,448503 | Risiko Rendah | 9 dari 9 di bawah acuan tahunan |

Klaster 2 dan 3 memiliki pola berbeda, tetapi keduanya memenuhi aturan kategori yang sama. Pada Klaster 2, centroid selang tertindih bernilai 0,515902; indeks gas yang merupakan rata-rata lima indikator tetap 0,433517. Aturan menggunakan rata-rata kelompok, bukan nilai maksimum satu indikator. Batas kategori 0,5 tetap dipertahankan. Z=0 dipakai sebagai acuan deskripsi posisi centroid terhadap rata-rata tahun masing-masing, tanpa membuat kategori risiko baru.

## Pemeriksaan alur dan perbaikan

`build_profiles` membentuk centroid dari label asli AHC, lalu mengurutkan nomor final berdasarkan indeks gabungan. Profil dipetakan ke anggota melalui nomor klaster dengan relasi many-to-one. Penghitungan ulang dari sembilan Z-score anggota mengonfirmasi seluruh centroid, indeks, kategori, dan jumlah anggota tersebut.

Modul baru `firewatch/profiles.py` menggabungkan data standardisasi dengan anggota model melalui identitas kota–kecamatan–kelurahan, kemudian menghitung ulang karakteristik per nomor klaster. Modul memeriksa kesesuaian identitas anggota, nomor klaster, sembilan centroid, dua indeks, kategori setiap anggota, dan jumlah kelurahan terhadap profil model final. Profil atau indeks yang tertukar ditolak, sehingga tidak dapat dipakai diam-diam oleh tampilan. Pemeriksaan tidak melatih ulang model atau menulis ulang hasilnya.

Khusus AHC, ringkasan dan tooltip kini menampilkan deskripsi karakteristik yang dihitung dari tanda setiap centroid, diikuti kategori risiko asli dan nilai kedua indeks. Deskripsi ini tidak memakai daftar tetap berdasarkan Klaster 1/2/3. Bagian **Dasar interpretasi AHC** menampilkan seluruh statistik dan aturan kategorinya. Statistik berasal dari semua anggota model final dan tetap sama saat filter tampilan berubah; jumlah serta proporsi irisan tetap mengikuti hasil filter.

Tampilan serta hasil K-Means dan Spectral Bridges dipertahankan. Masukan Z-score, anggota seluruh klaster, centroid, kategori, K optimal, metrik setiap kandidat dan metrik final sebelum–sesudah identik secara numerik. Dataset tidak diubah; SHA-256 tetap `9cc540c37b870a70cbb56b8fd57ce9e233908de5589b1b04f3602fbedcbc7647`. Versi pipeline tetap 1.1.0 dan versi label tetap 2.

Seluruh **55 tes lulus**, termasuk regresi 81 metrik penelitian, pencocokan karakteristik dengan centroid anggota, pemetaan melalui identitas saat baris/nomor diacak, pendeteksian centroid tertukar atau label salah, serta pemeriksaan tampilan dan filter. Angka lengkap sembilan indikator dan hasil perbandingan tersimpan pada [verifikasi-profil-ahc.json](verifikasi-profil-ahc.json).

Pemeriksaan browser lokal mengonfirmasi tiga irisan AHC, jumlah dan proporsi 1/128/138 serta 0,4%/47,9%/51,7%, karakteristik centroid yang berbeda, dan indeks sesuai tabel audit. Bagian Dasar interpretasi AHC dapat dibuka untuk memeriksa aturan serta statistik seluruh anggota. Bukti tampilan: [karakteristik AHC terverifikasi](screenshots/ahc-karakteristik-terverifikasi.png).
