Judul Skripsi:
**Klasterisasi Kelurahan Berdasarkan Indikator Kerawanan Kebakaran di DKI Jakarta Menggunakan Metode K-Means, Hierarchical Clustering, dan Spectral Bridges**

### 1. HALAMAN BERANDA:
Halaman beranda ini berisi
- Judul: Klasterisasi Kelurahan Berdasarkan Indikator Kerawanan Kebakaran di DKI Jakarta Menggunakan Metode K-Means, Hierarchical Clustering, dan Spectral Bridges
- Tujuan:
    - Mengelompokkan kelurahan di DKI Jakarta berdasarkan indikator kerawanan kebakaran
    - Menghasilkan performa klasterisasi yang baik, divalidasi menggunakan metrik evaluasi
- Manfaat:
    - Menghasilkan profil kerawanan kebakaran yang lebih utuh dan terperinci, berdasarkan integrasi indikator kondisi fisik seperti gas dan kelistrikan yang didukung bersama data kepadatan penduduk
    - Menghasilkan visualisasi kerawanan kebakaran untuk pengguna awam dan nonteknis mudah dalam memahami dan menginterpretasi
    - Memberikan kontribusi nyata bagi instasi terkait, dalam penyusunan strategi prioritas mitigasi yang lebih efektif, tepat sasaran, dan berbasis data.
- Penjelasan Indikator:

<table>
  <thead>
    <tr>
      <th>Variabel</th>
      <th>Keterangan</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td colspan="2"><b>Kondisi Kelistrikan</b></td>
    </tr>
    <tr>
      <td>steker_menumpuk</td>
      <td>Persentase pemakaian steker bertumpuk yang melebihi kapasitas.</td>
    </tr>
    <tr>
      <td>steker_hangus</td>
      <td>Persentase kondisi steker listrik yang rusak akibat panas.</td>
    </tr>
    <tr>
      <td>stopkontak_kendur</td>
      <td>Persentase kondisi stopkontak yang longgar kerapatannya.</td>
    </tr>
    <tr>
      <td>kabel_rusak</td>
      <td>Persentase kondisi fisik kabel listrik yang rusak.</td>
    </tr>
    <tr>
      <td colspan="2"><b>Kondisi Gas</b></td>
    </tr>
    <tr>
      <td>tabung_rusak</td>
      <td>Persentase kondisi tabung gas yang cacat.</td>
    </tr>
    <tr>
      <td>selang_longgar</td>
      <td>Persentase alat pengikat selang gas yang kendur.</td>
    </tr>
    <tr>
      <td>regulator_rusak</td>
      <td>Persentase kondisi regulator yang rusak.</td>
    </tr>
    <tr>
      <td>selang_tertindih</td>
      <td>Persentase kondisi selang gas yang terjepit benda berat.</td>
    </tr>
    <tr>
      <td>kompor_berdekatan</td>
      <td>Persentase tata letak dua kompor gas yang berdekatan.</td>
    </tr>
  </tbody>
</table>

2. SIDEBAR: Posisinya disebelah kiri, berguna dalam Navigasi utama aplikasi dalam berpindah halama, isinya daftar menu yang mengarah ke berbagai halaman.
3. HALAMAN DATASET:
    - Data awal yang digunakan adalah dataset “2425.csv”
    - Menampilkan data mentah, dengan menggunakan dataset “2425.csv” dalam bentuk tabel interaktif (melihat, menyortir, mencari, memfilter dll)
    - Menyediakan button unduh dataset yang terhubung ke link Google Drive berikut dalam bentuk .csv:
      <u>https://drive.google.com/file/d/12J4vocfVVSWSYdBPMfmMsRDMEY1lKooD/view?usp=sharing</u>
      yang dimana otomatis terdownload ke device user.
    - Menyediakan area untuk user upload dataset yang sudah didownload, setelah user upload dataset, sistem langsung menampilkan data mentah dalam bentuk tabel interaktif seperti di poin awal.
4. HALAMAN KLASTERISASI:
    - Dataset yang diupload di HALAMAN DATASET, diolah di halaman ini. Jadi halaman dataset dan halaman klasterisasi terhubung secara fungsional, jadi apa yang diupload di halaman dataset akan diolah di halaman klasterisasi
    - Proses
        1. Variabel yang diolah adalah 9 indikator persentase kerawanan kebakaran, variabel kepadatan penduduk, koordinat kelurahan, dan informasi lainnya akan digunakan nanti saat klasterisasi dihasilkan.
        2. Di latar belakang, sistem akan otomatis melakukan standarisasi data 9 indikator secara terpisah menggunakan Z-Score
        3. Selanjutnya melakukan Agregasi rata-rata data, yang tadinya 1 baris kelurahan ada di 2 periode berbeda menjadi 1 baris berisi 1 baris kelurahan. Yang tadinya 534 baris menjadi 267 baris kelurahan.
        4. KLASTERISASI K-MEANS:
            a. Sistem akan otomatis mencari Klaster Optimal dari rentang 2 klaster sampai 10 klaster yang divalidasi dengan Metrik Evaluasi Silhouette Score, Davies Bouldin Index, dan Calinski Harabasz Index. Random State yang digunakan adalah 11. Bilamana ketiga metrik tersebut saling bertolak belakang dalam pemilihan klaster optimal yang sama, maka keputusan diambil berdasarkan jumlah klaster yang paling banyak didukung oleh dua atau lebih metrik evaluasi. Untuk refrensi kode program dalam mencari klaster optimal seperti berikut:

```python
import time
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, davies_bouldin_score, calinski_harabasz_score

hasil_eksperimen_kmeans = []
print("EKSPERIMEN K-MEANS")
print("RANDOM STATE (11)")
print(f"{'K':<5} {'Random_State':<14} {'Silhouette':<12} {'DBI':<10} {'CHI':<12} {'Waktu(s)':<10}")
```

```python
print("=" * 65)

for k in range(2, 11):
    try:
        start = time.time()
        model = KMeans(n_clusters=k, random_state=11, n_init=10)
        labels = model.fit_predict(X)
        elapsed = time.time() - start

        # Pastikan minimal terbentuk 2 cluster
        if len(np.unique(labels)) < 2:
            continue

        sil = silhouette_score(X, labels)
        dbi = davies_bouldin_score(X, labels)
        chi = calinski_harabasz_score(X, labels)

        hasil_eksperimen_kmeans.append({
            'k': k,
            'random_state': 11,
            'silhouette': round(sil, 4),
            'dbi': round(dbi, 4),
            'chi': round(chi, 4),
            'waktu_detik': round(elapsed, 4)
        })

        print(f"{k:<5} {11:<14} {sil:<12.4f} {dbi:<10.4f} {chi:<12.4f} {round(elapsed, 4):<10}")

    except Exception as e:
        print(f"Gagal pada k={k}: {e}")
        continue
```

b. Lakukan Klasterisasi Final menggunakan Klaster Optimal yang sudah dicari
c. Hitung metrik evaluasi final pakai ketiga metrik evaluasi (Silhouette, DBI, dan CHI)
d. Memberikan label interpretasi setiap kelurahan Menggunakan Z Score, dengan menghitung rata-rata nilai Centroid setiap klaster, dengan contoh perhitungan manual seperti berikut

## Analisis Interpretasi Klaster 1

$$*Ris\ k_{Gas}* = \frac{10.71 + 12.59 + 9.19 - 1.95 + 1.48}{5} = 6.40$$

$$*Ris\ k_{Listrik}* = \frac{-1.14 - 1.09 - 0.96 - 1.32}{4} = -1.13$$

Analisis Interpretasi Klaster 2

$$*Ris\ k_{Gas}* = \frac{0.03 + 0.80 + 0.54 + 1.32 + 0.03}{5} = 0.54$$

$$*Ris\ k_{Listrik}* = \frac{1.70 + 1.41 + 1.16 + 1.94}{4} = 1.55$$

Analisis Interpretasi Klaster 3

$$*Ris\ k_{Gas}* = \frac{0.20 + 0.03 + 0.85 + 0.26 - 0.39}{5} = 0.19$$

$$*Ris\ k_{Listrik}* = \frac{-1.01 - 0.54 - 0.80 - 0.15}{4} = -0.63$$

Dengan interpretasi indeks risiko seperti berikut:

<table>
  <thead>
    <tr>
      <th>Indeks Risiko</th>
      <th>Interpretasi</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><i>Risk<sub>Listrik</sub></i> > 0,5 ∧ <i>Risk<sub>Gas</sub></i> ≤ 0,5</td>
      <td>Dominan Bahaya Kelistrikan</td>
    </tr>
    <tr>
      <td><i>Risk<sub>Gas</sub></i> > 0,5 ∧ <i>Risk<sub>Listrik</sub></i> ≤ 0,5</td>
      <td>Dominan Bahaya Gas</td>
    </tr>
    <tr>
      <td><i>Risk<sub>Listrik</sub></i> > 0,5 ∧ <i>Risk<sub>Gas</sub></i> > 0,5</td>
      <td>Dominan Bahaya Keduanya</td>
    </tr>
    <tr>
      <td><i>Risk<sub>Listrik</sub></i> ≤ 0,5 ∧ <i>Risk<sub>Gas</sub></i> ≤ 0,5</td>
      <td>Risiko Aman</td>
    </tr>
  </tbody>
</table>

5. KLASTERISASI AHC:
    a. Sistem akan otomatis mencari Klaster Optimal dari rentang 2 klaster sampai 10 klaster yang divalidasi dengan Metrik Evaluasi Silhouette Score, Davies Bouldin Index, dan Calinski Harabasz Index. Bilamana ketiga metrik tersebut saling bertolak belakang dalam pemilihan klaster optimal yang sama, maka keputusan diambil berdasarkan jumlah klaster yang paling banyak didukung oleh dua atau lebih metrik evaluasi. Untuk refrensi kode program dalam mencari klaster optimal seperti berikut:

```python
from sklearn.cluster import AgglomerativeClustering
hasil_eksperimen_ahc = []
print("EKSPERIMEN AHC (Ward Linkage)")
print(f"{'K':<5} {'Silhouette':<12} {'DBI':<10} {'CHI':<12} {'Waktu(s)':<10}")
print("=" * 65)
for k in range(2, 11):
    best_silhouette = -1
    best_dbi = None
    best_chi = None
```

```python
    waktu_total = 0
    start = time.time()
    model = AgglomerativeClustering(n_clusters=k, linkage='ward')
    labels = model.fit_predict(X)
    elapsed = time.time() - start
    waktu_total += elapsed
    if len(np.unique(labels)) >= 2:
        best_silhouette = silhouette_score(X, labels)
        best_dbi = davies_bouldin_score(X, labels)
        best_chi = calinski_harabasz_score(X, labels)
    hasil_eksperimen_ahc.append({
        'k': k,
        'silhouette': round(best_silhouette, 4),
        'dbi': round(best_dbi, 4) if best_dbi is not None else None,
        'chi': round(best_chi, 4) if best_chi is not None else None,
        'waktu_total_detik': round(waktu_total, 4)
    })
    print(f"{k:<5} {best_silhouette:<12.4f} {round(best_dbi, 4):<10} {round(best_chi, 4):<12} {round(waktu_total, 5):<10}")
```

b. Lakukan Klasterisasi Final menggunakan Klaster Optimal yang sudah dicari
c. Hitung metrik evaluasi final pakai ketiga metrik evaluasi (Silhouette, DBI, dan CHI)
d. Seperti algoritma sebelumnya yaitu Memberikan label interpretasi setiap kelurahan Menggunakan Z Score, dengan menghitung rata-rata nilai Centroid setiap klaster.

**6. KLASTERISASI SPECTRAL BRIDGES:**
a. Sistem akan otomatis mencari Klaster Optimal dari rentang 2 klaster sampai 10 klaster yang divalidasi dengan Metrik Evaluasi Silhouette Score, Davies Bouldin Index, dan Calinski Harabasz Index. Random State yang digunakan adalah RS=549, n nodes=15, dan p=2. Bilamana ketiga metrik tersebut saling bertolak belakang dalam pemilihan klaster optimal yang sama, maka keputusan diambil berdasarkan jumlah klaster yang paling banyak didukung oleh dua atau lebih metrik evaluasi. Untuk refrensi kode program dalam mencari klaster optimal seperti berikut:

```python
pip install spectral-bridges
from spectralbridges import SpectralBridges
import time
import numpy as np
from sklearn.metrics import silhouette_score, davies_bouldin_score, calinski_harabasz_score

hasil_eksperimen = []
print("EVALUASI SPECTRAL BRIDGES (RANDOM STATE = 549)")
```

```python
print(f"{'K':<5} {'Random_State':<14} {'Silhouette':<12} {'DBI':<10} {'CHI':<12} {'Waktu(s)':<10}")
print("=" * 70)

for k in range(2, 11):
    try:
        start = time.time()
        model = SpectralBridges(n_clusters=k, n_nodes=15, p=2, random_state=549)
        model.fit(X)
        labels = model.predict(X)
        elapsed = time.time() - start

        # Pastikan ada minimal 2 cluster yang terbentuk
        if len(np.unique(labels)) < 2:
            continue

        sil = silhouette_score(X, labels)
        dbi = davies_bouldin_score(X, labels)
        chi = calinski_harabasz_score(X, labels)

        hasil_eksperimen.append({
            'k': k,
            'random_state': 549,
            'silhouette': round(sil, 4),
            'dbi': round(dbi, 4),
            'chi': round(chi, 4),
            'waktu_detik': round(elapsed, 4),
        })
        print(f"{k:<5} {549:<14} {sil:<12.4f} {dbi:<10.4f} {chi:<12.4f} {round(elapsed, 4):<10}")

    except Exception as e:
        print(f"Gagal pada k={k}: {e}")
        continue
```

b. Lakukan Klasterisasi Final menggunakan Klaster Optimal yang sudah dicari
c. Hitung metrik evaluasi final pakai ketiga metrik evaluasi (Silhouette, DBI, dan CHI)
d. Seperti algoritma sebelumnya yaitu Memberikan label interpretasi setiap kelurahan Menggunakan Z Score, dengan menghitung rata-rata nilai Centroid setiap klaster.

### 7. Penyajian Hasil:
- Setelah Sistem melakukan pencarian K optimal dan Klasterisasi dari masing-masing ketiga algoritma, selanjutnya adalah menyajikan hasil klasterisasi.

- Yang muncul duluan adalah hasil klasterisasi algoritma yang paling optimal atau yang memiliki nilai evaluasi tertinggi dari algoritma lainnya. Jadi penyajian hasil utamakan algoritma yang paling optimal. Walaupun user juga bisa melihat hasil dari klasterisasi kedua algoritma yang lain. Jadi user bisa klik tab Algoritma K-Means atau AHC atau Spectral Bridges
- Yang harus ada saat menyajikan hasil klasterisasi adalah kelurahan beserta dengan informasinya, hasil klaster setiap kelurahan, interpretasi Z Score setiap kelurahan, profilisasi kepadatan penduduk dll. Bisa anda kembangkan juga supaya memperjelas user nonteknis dalam membaca hasil klasterisasi. Tambahkan juga seperti grafik grafik dan lain lain.
- Selanjutnya juga menampilkan klaster optimal yang dipakai beserta dengan jumlah klaster saingannya dalam pencarian klaster optimal yang dilakukan sebelumnya.
- Menampilkan juga hasil evaluasi dari ketiga metrik evaluasi
- Tampilkan juga peta interaktif setiap kelurahan DKI Jakarta berdasarkan data Koordinat (latitude, longitude, dan elevasi) agar memudahkan user dalam melihat hasil klasterisasi
- Hasil klasterisasi yang ditampilkan bersifat tetap, karena parameter optimal dari kedua metode tersebut sudah ditentukan sistem, dan tidak dapat diubah oleh pengguna. Karena seluruh proses klasterisasi dijalankan oleh sistem. Jadi modul klasterisai pada dashboard ini hanya untuk menyajikan hasil klasterisasi yang diperuntukkan pengguna non teknis.

## 5. HALAMAN FAQ:
- menyajikan daftar pertanyaan beserta jawabannya yang sering ditanyakan seputar aplikasi, seperti cara membaca hasil klasterisasi, informasi terkait kerawanan kebakaran, tujuan dari aplikasi, mekanisme sistem dalam melakukan klasterisasi, maupun hal-hal yang relevan terkait penggunaan aplikasi.
- Modul ini tidak menyediakan fitur pengajuan pertanyaan baru.

## 6. HALAMAN ABOUT:
- menyediakan informasi terkait latar belakang sistem dan profil pengembang,
- modul ini bersifat informatif dan statis tidak menyediakan fitur interaktif.
- Nama: Mario Samuel Budiono (535230091) Teknik Informatika, FTI, UNTAR
- Dosen Pembimbing: Dr. Bagus Mulyawan, S.Kom., M.M.
- Email: mario.535230091@stu.untar.ac.id

Buatkan dashboard web sederhana menggunakan STREAMLIT, kembangkan lagi jika diperlukan supaya lebih efisien, untuk desain website lebih yang memudahkan user nonteknis dalam membaca, desain profesional sesuai dengan topik mitigasi kebakaran