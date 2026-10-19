"""Dataset makanan terkurasi (249 item inti setelah penghapusan duplikasi konseptual) beserta harga per porsi, alasan, dan saran makan; pemilihan menu berbasis aturan.
Makanan tambahan dari penelusuran web disimpan di dataset_web.json dan ikut dimuat di sini (hanya untuk tanya jawab, tidak dipakai menyusun jadwal karena alerginya belum terverifikasi).
Format baris: kode_kategori|nama|gram|kilokalori|protein|karbohidrat|lemak|serat|kata_kunci_gambar (bahasa Inggris, untuk mencari foto).
Atribut lain (indeks glikemik, natrium, purin, kolesterol, lambung, jenis, alergen) diturunkan oleh aturan kata kunci
di _atribut(); tinjau dan ubah daftar kata kunci jika ada yang kurang tepat."""
import re, random, os, json, threading
import knowledge as kb
import penjelasan

KAT = {"K": "Karbohidrat", "P": "Protein", "S": "Sayuran", "B": "Buah", "L": "Lemak sehat dan camilan", "H": "Hidangan olahan sehat"}
BARIS = """
K|Beras merah matang|150|165|4|35|1.3|2.7|cooked brown rice
K|Oatmeal|40|150|5|27|3|4|oatmeal porridge
K|Ubi jalar rebus|150|130|2|31|0.2|4.5|boiled sweet potato
K|Kentang rebus|150|130|3|30|0.2|3|boiled potatoes
K|Roti gandum utuh|60|150|7|26|2|4|whole wheat bread
K|Jagung manis rebus|150|130|4|29|1.5|4|boiled corn on the cob
K|Pasta gandum utuh matang|100|150|6|30|1.5|4|whole wheat pasta
K|Couscous matang|100|112|3.8|23|0.2|1.4|couscous
K|Bulgur matang|150|125|4.5|28|0.4|6|cooked bulgur
K|Polenta|150|120|3|26|0.5|2|polenta
K|Granola rendah gula|40|180|4.5|26|7|3|granola
K|Mi soba matang|100|99|5|21|0.1|1.5|cooked soba noodles
K|Roti pita gandum|60|150|5.5|31|1.5|4.5|whole wheat pita bread
K|Quinoa rebus|150|180|6.6|32|3|4|cooked quinoa
K|Tortilla gandum|50|140|4|24|3|3|whole wheat tortilla
K|Roti sourdough|60|150|6|29|1|1.5|sourdough bread
K|Roti rye|60|150|5|30|1.5|4.5|rye bread
K|Barley matang|150|160|4|34|1|6|cooked pearl barley
K|Kentang panggang|150|140|3.5|32|0.2|3.5|baked potato
K|Ubi jalar panggang|150|150|2|36|0.2|4|baked sweet potato
K|Farro matang|150|190|7|38|1.5|5|cooked farro
P|Dada ayam panggang|100|165|31|0|3.6|0|grilled chicken breast
P|Dada ayam kukus|100|140|28|0|3|0|poached chicken breast
P|Dada kalkun panggang|100|135|30|0|1.5|0|roast turkey breast
P|Paha ayam panggang tanpa kulit|100|180|26|0|8|0|roasted chicken thigh
P|Tilapia panggang|100|130|26|0|3|0|baked tilapia fillet
P|Makerel panggang|100|230|22|0|15|0|grilled mackerel
P|Cod panggang|100|105|23|0|0.9|0|baked cod fillet
P|Sarden panggang|100|210|25|0|11.5|0|grilled sardines
P|Trout panggang|100|150|21|0|7|0|baked trout
P|Tuna panggang|100|130|29|0|1|0|seared tuna steak
P|Sea bass panggang|100|125|24|0|2.6|0|baked sea bass
P|Haddock panggang|100|112|24|0|0.9|0|baked haddock
P|Salmon panggang|100|200|22|0|12|0|grilled salmon fillet
P|Scallop panggang|100|110|21|3|1|0|seared scallops
P|Udang rebus|100|100|20|0.2|1.7|0|boiled shrimp
P|Cumi rebus|100|90|15.6|3|1.4|0|cooked squid
P|Telur rebus|55|78|6|0.6|5|0|boiled egg
P|Telur puyuh rebus|45|70|6|0.2|5|0|boiled quail eggs
P|Putih telur rebus|100|52|11|0.7|0.2|0|boiled egg whites
P|Steak sirloin panggang|100|190|28|0|8|0|grilled sirloin steak
P|Yogurt plain|150|90|8|11|2.5|0|plain yogurt bowl
P|Yogurt Yunani tanpa gula|150|90|15|6|0.5|0|greek yogurt
P|Susu rendah lemak|200|90|7|10|2|0|glass of milk
P|Keju cottage|100|98|11|3.4|4.3|0|cottage cheese
P|Tofu panggang|100|90|9|2|5.5|1|baked tofu
P|Hummus|60|100|5|8|6|3.5|hummus
P|Kacang merah rebus|90|110|8|20|0.4|6|cooked kidney beans
P|Edamame rebus|100|120|11|9|5|5|edamame
P|Kacang arab rebus|90|145|8|24|2.3|7|cooked chickpeas
P|Kacang putih rebus|100|140|9|25|0.5|6|cooked white beans
P|Kacang polong rebus|100|80|5|14|0.4|5.5|cooked green peas
P|Lentil rebus|100|116|9|20|0.4|7.9|cooked lentils
P|Susu kedelai tanpa gula|200|80|7|4|4|1|soy milk
P|Tuna kaleng dalam air|100|116|26|0|1|0|canned tuna
S|Brokoli kukus|100|35|2.8|7|0.4|2.6|steamed broccoli
S|Bayam rebus|100|25|3|4|0.4|2.5|cooked spinach
S|Wortel rebus|100|35|0.8|8|0.2|3|boiled carrots
S|Kale tumis|100|60|3|6|3|2.5|sauteed kale
S|Sup minestrone|250|120|5|20|2|4|minestrone soup
S|Salad hijau dengan lemon|150|70|3|10|2.5|4|green salad
S|Salad timun dan tomat|150|30|1.5|6|0.3|1.5|cucumber tomato salad
S|Buncis rebus|100|35|1.9|8|0.2|3.2|steamed green beans
S|Kubis kukus|100|25|1.3|6|0.1|2.5|steamed cabbage
S|Zucchini panggang|100|25|1.5|4.5|0.4|1.5|grilled zucchini
S|Terong panggang|100|35|1|9|0.2|3|roasted eggplant
S|Asparagus panggang|100|25|2.4|4|0.2|2|roasted asparagus
S|Swiss chard tumis|100|50|2|4|3|2|sauteed swiss chard
S|Labu butternut panggang|100|45|1|12|0.1|2|roasted butternut squash
S|Brussels sprout panggang|100|45|3.4|9|0.3|3.8|roasted brussels sprouts
S|Sayur panggang campur|150|100|3|14|4|4|roasted vegetables
S|Kembang kol kukus|100|25|2|5|0.3|2.5|steamed cauliflower
S|Paprika panggang|100|35|1|7|0.4|2.5|roasted bell peppers
S|Artichoke kukus|120|60|4|13|0.2|7|steamed artichoke
S|Selada segar|100|15|1.4|2.9|0.2|1.3|fresh lettuce
S|Sup tomat|250|90|3|15|2|3|tomato soup
S|Ratatouille|200|130|3|16|6|5|ratatouille
S|Salad arugula|100|25|2.6|3.7|0.7|1.6|arugula salad
S|Tabbouleh|150|130|3|15|7|4|tabbouleh
S|Jamur panggang|100|60|3|5|3|2|grilled mushrooms
S|Sup brokoli|250|70|3|10|2|3|broccoli soup
S|Coleslaw ringan|100|40|1.3|9|0.2|2.5|coleslaw
S|Salad bit|150|75|2.5|16|0.5|3.5|beetroot salad
S|Tomat panggang|100|40|1|8|0.5|2|roasted tomatoes
S|Seledri dan wortel stik|100|25|1|6|0.2|2.5|celery and carrot sticks
S|Kembang kol panggang|100|40|2|6|1.5|2.5|roasted cauliflower
S|Sup miso sayur|250|60|4|7|2|1.5|miso soup
B|Apel|180|95|0.5|25|0.3|4.4|apple fruit
B|Pisang|120|105|1.3|27|0.4|3|banana fruit
B|Jeruk|130|62|1.2|15|0.2|3|orange fruit
B|Pepaya|150|65|0.7|16|0.3|2.5|papaya fruit
B|Persik|150|59|1.4|14|0.4|2.3|peach fruit
B|Semangka|200|60|1.2|15|0.3|0.8|watermelon slice
B|Melon|150|50|1.2|12|0.3|1.4|cantaloupe melon
B|Mangga|100|60|0.8|15|0.4|1.6|mango fruit
B|Nanas|100|50|0.5|13|0.1|1.4|pineapple fruit
B|Buah ara|100|74|0.8|19|0.3|2.9|fresh figs
B|Pir|150|85|0.5|23|0.2|5|pear fruit
B|Anggur|100|70|0.7|18|0.2|0.9|grapes
B|Plum|130|60|0.9|15|0.4|2|plum fruit
B|Stroberi|100|32|0.7|7.7|0.3|2|strawberries
B|Salad buah tanpa gula|150|90|1.5|22|0.5|3|fruit salad
B|Kiwi|70|42|0.8|10|0.4|2.1|kiwi fruit
B|Ceri|100|63|1|16|0.2|2.1|cherries
B|Grapefruit|150|50|1|13|0.2|2|grapefruit
B|Aprikot|105|50|1.5|11.5|0.4|2|apricots
B|Delima|100|83|1.7|19|1.2|4|pomegranate
B|Raspberry|100|52|1.2|12|0.7|6.5|raspberries
B|Blackberry|100|43|1.4|10|0.5|5.3|blackberries
B|Nektarin|140|62|1.5|15|0.5|2.4|nectarine
B|Blueberry|100|57|0.7|14|0.3|2.4|blueberries
B|Kurma|40|110|0.7|29|0.1|3|dates fruit
L|Alpukat|100|160|2|9|15|7|avocado
L|Almond|28|165|6|6|14|3.5|almonds
L|Kenari|28|185|4.3|3.9|18.5|1.9|walnuts
L|Popcorn polos|25|95|3|19|1|3.6|popcorn
L|Kacang mete panggang|28|160|5|9|12|1|cashew nuts
L|Pistachio|28|160|6|8|13|3|pistachio nuts
L|Biji chia|12|58|2|5|3.7|4.1|chia seeds
L|Cokelat hitam 85%|20|120|1.7|6|9|2.5|dark chocolate
H|Omelet sayur|100|120|7|3|9|1|vegetable omelette
H|Sup ayam sayur|250|120|12|9|4|2|chicken vegetable soup
H|Tofu sayur tumis|150|140|9|10|8|3|stir fried tofu vegetables
H|Salad Yunani|250|220|7|11|17|3|greek salad
H|Salad Nicoise|300|300|22|15|16|4|nicoise salad
H|Poke bowl salmon|350|450|28|50|15|5|salmon poke bowl
H|Sup lentil|250|180|12|28|2|9|lentil soup
H|Tofu teriyaki|150|170|12|12|8|2|teriyaki tofu
H|Burrito bowl ayam|350|480|30|55|14|9|chicken burrito bowl
H|Ayam teriyaki|150|240|24|10|11|0.5|teriyaki chicken
H|Bowl ayam panggang beras merah|400|520|36|60|12|6|grilled chicken brown rice bowl
H|Bowl salmon quinoa|400|560|34|50|22|7|salmon quinoa bowl
H|Beef stew sayur|300|250|24|12|10|2|beef stew
H|Shish kebab ayam|150|220|27|5|10|1|chicken shish kebab
H|Salad kacang arab|200|250|10|30|9|8|chickpea salad
H|Wrap ayam sayur|250|380|24|40|12|5|chicken wrap
H|Bola daging kalkun|150|230|24|8|11|1|turkey meatballs
H|Pasta ayam brokoli|350|430|30|50|11|6|chicken broccoli pasta
H|Ayam panggang lemon herba|150|210|25|3|11|1|lemon herb roasted chicken
H|Falafel panggang|150|260|11|28|11|7|baked falafel
H|Scrambled egg bayam|120|150|9|4|11|1|scrambled eggs spinach
H|Sup telur|250|140|12|8|7|1|egg drop soup
H|Risotto jamur ayam|250|320|18|45|8|2|mushroom risotto
H|Tofu scramble|150|130|11|6|7|2.5|tofu scramble
H|Salad ayam panggang|250|250|24|12|11|4|grilled chicken salad
H|Sup sayur campur|250|90|4|12|3|3|vegetable soup
H|Paella seafood|300|380|24|48|9|3|seafood paella
H|Sup labu butternut|250|110|3|20|3|3|butternut squash soup
H|Shakshuka|250|220|13|14|13|4|shakshuka
"""
# 100 makanan Indonesia murah sampai sedang. Kolom ke-10 = harga per porsi (Rupiah), perkiraan harga warung/rumahan.
# Acuan harga (Januari 2026, Panel Harga Badan Pangan Nasional): beras medium sekitar Rp13.300/kg, daging ayam ras sekitar Rp38.700/kg,
# telur ayam ras sekitar Rp30.500/kg, daging sapi sekitar Rp135.000/kg, ikan tongkol sekitar Rp36.000/kg, ikan kembung sekitar Rp43.000/kg.
# Acuan warung (2024-2026): nasi sayur Rp4.000-6.000, nasi ayam sayur sekitar Rp20.000, paket nasi ikan sayur sekitar Rp13.000, soto atau bubur Rp8.000-10.000.
BARIS_ID = """
K|Nasi putih|150|195|4|42|0.5|0.6|steamed rice|4000
K|Nasi merah|150|165|4|35|1.3|2.7|brown rice|5000
K|Nasi jagung|150|150|3.5|32|1|3|corn rice|4000
K|Nasi gandum|150|170|4.5|36|1.2|3.5|whole grain rice|5000
K|Ubi ungu kukus|150|135|2|32|0.2|4|steamed purple sweet potato|3500
K|Ubi cilembu panggang|150|150|2|36|0.2|4|roasted sweet potato|5000
K|Singkong rebus|100|160|1.4|38|0.3|1.8|boiled cassava|2500
K|Talas rebus|100|112|1.5|26|0.2|4.1|boiled taro|3000
K|Sukun rebus|100|110|1.1|26|0.2|3.9|boiled breadfruit|3000
K|Lontong|100|100|2|22|0.2|0.5|lontong rice cake|2500
K|Ketupat|100|110|2.2|24|0.3|0.4|ketupat rice cake|3000
K|Bubur nasi polos|200|100|2|22|0.3|0.3|plain rice porridge|5000
K|Mi gandum rebus|100|138|4.5|25|2|1.2|boiled noodles|4000
K|Bihun rebus|100|110|1.5|26|0.1|0.7|boiled rice vermicelli|3500
P|Ayam bakar tanpa kulit|100|175|27|0|7|0|grilled chicken|8000
P|Ayam rebus tanpa kulit|100|150|29|0|3|0|boiled chicken breast|7000
P|Pepes ayam|150|210|25|3|11|1|steamed chicken banana leaf|9000
P|Ayam suwir kemangi|100|170|22|3|8|0.5|shredded chicken basil|8000
P|Ikan kembung bakar|100|170|22|0|9|0|grilled mackerel|7000
P|Ikan lele panggang|100|140|17|0|7|0|grilled catfish|7000
P|Ikan tongkol kukus|100|140|25|0|4|0|steamed skipjack tuna|6000
P|Ikan patin kukus|100|120|16|0|6|0|steamed pangasius|8000
P|Ikan bandeng panggang|100|150|20|0|7|0|grilled milkfish|8000
P|Ikan gurame bakar|100|130|24|0|3.5|0|grilled gourami|12000
P|Ikan kakap kukus|100|110|24|0|1.5|0|steamed snapper|14000
P|Pepes ikan|100|140|18|3|6|1|steamed fish banana leaf|8000
P|Daging sapi rebus tanpa lemak|100|190|28|0|8|0|boiled lean beef|15000
P|Tahu kukus|100|80|8|2|5|1|steamed tofu|2000
P|Tahu isi sayur kukus|100|100|8|6|4.5|1.5|steamed stuffed tofu|3000
P|Tempe panggang|50|95|10|5|5|2|grilled tempeh|1500
P|Oncom bakar|50|90|5|9|3.5|3|grilled oncom|1500
P|Kacang hijau rebus|100|105|7|19|0.4|7.6|boiled mung beans|3000
P|Bubur kacang hijau|200|170|8|30|2|6|mung bean porridge|6000
P|Kacang tanah rebus|30|115|5|4|9|2.4|boiled peanuts|2500
S|Tumis kangkung|100|60|3|6|3|2.5|stir fried water spinach|4000
S|Kangkung rebus|100|20|2|3|0.2|2.5|boiled water spinach|2500
S|Sayur bening bayam|250|45|2.5|7|0.8|2.5|spinach soup|5000
S|Sayur asem|250|60|2|12|0.5|3|sayur asem vegetable soup|6000
S|Sayur sop|250|90|4|12|3|3|vegetable soup|6000
S|Sup sayur bening|200|40|2|7|0.5|2.5|clear vegetable soup|5000
S|Sup brokoli wortel|250|70|3|10|2|3|broccoli carrot soup|6500
S|Capcay sayur|150|100|5|10|4|3|chinese mixed vegetables|8000
S|Urap sayur|150|130|4|12|7|5|urap vegetables coconut|7000
S|Tumis buncis|100|70|2|7|4|3|stir fried green beans|4000
S|Oseng kacang panjang|100|75|2.5|7|4|3|stir fried long beans|4000
S|Tumis tauge|100|70|3.5|6|3.5|2|stir fried bean sprouts|3500
S|Tauge rebus|100|30|3|6|0.2|1.8|boiled bean sprouts|2500
S|Tumis sawi hijau|100|55|2|4|3.5|2|stir fried mustard greens|4000
S|Tumis pakcoy|100|45|1.5|3|3|1.5|stir fried bok choy|5000
S|Tumis jamur|100|60|3|5|3|2|stir fried mushrooms|6000
S|Tumis pare|100|45|2|7|1.5|3|stir fried bitter melon|4500
S|Tumis kailan|100|50|2|5|2.5|2.5|stir fried kailan|5500
S|Tumis jagung muda|100|85|2.5|10|4|2.5|stir fried baby corn|5000
S|Daun singkong rebus|100|40|3.5|7|0.5|3|boiled cassava leaves|3000
S|Labu siam rebus|100|20|0.8|4.5|0.1|1.7|boiled chayote|2500
S|Labu kuning kukus|100|26|1|6.5|0.1|0.5|steamed pumpkin|2500
S|Lalapan segar|100|20|1.5|3.5|0.3|2|fresh vegetables lalapan|3000
S|Rebusan sawi putih|100|15|1.5|2.2|0.2|1|boiled napa cabbage|3000
S|Timun dan tomat segar|150|30|1.5|6|0.3|1.5|cucumber tomato salad|3000
B|Jambu biji|100|68|2.6|14|1|5.4|guava|3000
B|Jambu air|100|25|0.6|5.7|0.3|1|water apple|4000
B|Salak|100|77|0.4|20|0.1|2.6|salak snake fruit|4000
B|Belimbing|100|31|1|6.7|0.3|2.8|star fruit|3500
B|Jeruk bali|150|60|1.2|15|0.1|2|pomelo|5000
B|Markisa|50|49|2.2|11.6|0.4|10|passion fruit|4000
B|Lengkeng|100|60|1.3|15|0.1|1.1|longan|8000
B|Rambutan|100|68|0.9|16|0.2|0.9|rambutan|4000
B|Sirsak|100|66|1|17|0.3|3.3|soursop|5000
B|Buah naga|100|60|1.2|13|0.4|3|dragon fruit|6000
B|Sawo|100|83|0.4|20|1.1|5.3|sapodilla|5000
B|Duku|100|63|1|16|0.2|1|langsat|8000
B|Nangka|100|95|1.7|23|0.6|1.5|jackfruit|6000
B|Bengkuang|100|38|0.7|8.8|0.1|4.9|jicama|3000
B|Manggis|100|73|0.4|18|0.6|1.8|mangosteen|12000
L|Biji labu|28|160|8.5|3|13.5|1.7|pumpkin seeds|9000
L|Biji bunga matahari|28|165|5.8|6|14|2.4|sunflower seeds|5000
L|Air kelapa muda|200|40|0.7|9|0.4|1|young coconut water|8000
L|Daging kelapa muda|100|70|0.7|15|1|3|young coconut meat|6000
H|Soto ayam bening|250|150|15|8|6|1|indonesian chicken soup soto|12000
H|Soto bening sayur|250|80|4|12|2|3|vegetable soup soto|8000
H|Gado-gado|250|250|11|24|13|7|gado gado salad|13000
H|Pecel sayur|200|200|8|20|10|6|pecel vegetables peanut sauce|10000
H|Karedok|200|170|7|15|9|6|karedok raw vegetables|9000
H|Ketoprak|300|330|13|45|11|5|ketoprak|12000
H|Pepes tahu|100|110|8|5|7|1.5|steamed tofu banana leaf|4000
H|Bubur ayam tanpa kerupuk|250|280|12|45|5|1.5|chicken congee|12000
H|Sup ikan bening|250|110|14|5|3|1|clear fish soup|12000
H|Ayam geprek panggang|150|250|27|8|12|1|smashed grilled chicken sambal|13000
H|Nasi padang ayam bakar sayur|400|650|32|85|20|6|nasi padang grilled chicken|18000
H|Nasi padang ikan bakar sayur|400|600|30|85|15|6|nasi padang grilled fish|18000
H|Rawon tanpa nasi|300|250|24|8|13|2|rawon beef soup|18000
H|Sate ayam bumbu kacang|150|300|26|10|17|1.5|chicken satay peanut sauce|15000
H|Bakso tanpa mi|200|230|15|12|14|1|bakso meatball soup|13000
H|Mi ayam|350|375|14|55|11|3|mie ayam chicken noodles|13000
H|Tumis tempe kacang panjang|150|170|10|12|9|5|tempeh long bean stir fry|6000
H|Orak-arik telur sayur|120|150|9|4|11|1|scrambled eggs vegetables|7000
H|Sup tahu telur|250|140|12|8|7|1|tofu egg soup|8000
H|Nasi tim ayam jamur|250|300|15|45|6|2|steamed chicken rice|12000
H|Cah tauge tahu|150|130|9|8|7|2.5|stir fried bean sprouts tofu|6000
H|Capcay seafood|200|150|14|10|6|3|seafood stir fry vegetables|18000
"""

IG_T = ("beras putih", "kentang panggang", "risotto", "paella", "poke")
IG_S = ("beras merah", "ubi", "kentang", "jagung", "polenta", "roti", "pita", "tortilla", "wrap", "pasta", "soba", "couscous", "bulgur",
        "farro", "barley", "granola", "quinoa", "butternut", "pisang", "pepaya", "semangka", "melon", "mangga", "nanas", "anggur",
        "salad buah", "kurma", "popcorn", "delima", "buah ara", "burrito", "bowl", "minestrone")
NA_T = ("beef stew", "teriyaki", "miso", "paella", "tuna kaleng", "sup telur", "salad yunani", "nicoise", "burrito", "kebab")
NA_S = ("tumis", "sup", "salad", "roti", "pita", "tortilla", "wrap", "keju", "udang", "cumi", "scallop", "bowl", "pasta", "omelet",
        "scrambled", "shakshuka", "falafel", "hummus", "bola daging", "ratatouille", "tabbouleh", "granola", "sarden", "tofu scramble", "risotto")
PU_T = ("udang", "cumi", "sirloin", "beef", "bola daging", "sarden", "makerel", "scallop", "paella", "tuna kaleng")
PU_S = ("ayam", "kalkun", "ikan", "salmon", "tilapia", "cod", "trout", "tuna", "bass", "haddock", "nicoise", "poke", "tofu", "edamame",
        "kacang", "lentil", "kedelai", "bayam", "jamur", "asparagus", "kembang kol", "kebab", "hummus", "falafel", "swiss chard", "bowl")
LAMBUNG = ("jeruk", "nanas", "delima", "stroberi", "kiwi", "grapefruit", "lemon", "tomat", "shakshuka", "ratatouille", "teriyaki")


def _atribut(n):
    ada = lambda *k: any(re.search(r"\b" + re.escape(x), n) for x in k)
    al = []
    if ada("ikan", "tilapia", "makerel", "cod", "sarden", "trout", "tuna", "sea bass", "haddock", "salmon", "nicoise", "poke"): al.append("ikan")
    if ada("udang", "paella"): al += ["udang", "seafood"]
    if ada("cumi", "seafood", "scallop"): al.append("seafood")
    if ada("telur", "omelet", "scrambled", "shakshuka", "nicoise"): al.append("telur")
    if ada("tofu", "edamame", "kedelai", "miso", "teriyaki"): al.append("kedelai")
    if ada("susu", "yogurt", "keju", "yunani") and not ada("kedelai"): al.append("susu")
    if ada("roti", "pita", "tortilla", "wrap", "pasta", "soba", "couscous", "bulgur", "farro", "barley", "granola", "tabbouleh", "gandum", "minestrone"): al.append("gluten")
    if ada("almond", "kenari", "mete", "pistachio"): al.append("kacang pohon")
    if ada("hummus", "falafel"): al.append("wijen")
    return dict(
        je="hewani" if ada("ayam", "kalkun", "sirloin", "beef", "bola daging") else
        "ikan" if ada("ikan", "tilapia", "makerel", "cod", "sarden", "trout", "tuna", "bass", "haddock", "salmon", "scallop", "udang", "cumi", "seafood", "paella", "nicoise", "poke")
        else "telur_susu" if ada("telur", "omelet", "scrambled", "shakshuka", "yogurt", "keju", "susu", "yunani") and not ada("kedelai") else "nabati",
        ig="tinggi" if ada(*IG_T) else "sedang" if ada(*IG_S) else "rendah",
        na="tinggi" if ada(*NA_T) else "sedang" if ada(*NA_S) else "rendah",
        pu="tinggi" if ada(*PU_T) else "sedang" if ada(*PU_S) else "rendah",
        ko="tinggi" if ada("udang", "cumi", "sirloin", "beef", "bola daging", "paella") or (ada("telur", "omelet", "scrambled", "shakshuka", "nicoise") and not ada("putih telur"))
        else "sedang" if ada("ayam", "kalkun", "keju", "seafood", "scallop", "kebab", "yunani") else "rendah",
        la="iritatif" if ada(*LAMBUNG) else "aman", al=list(dict.fromkeys(al)))


def _tambah_id(n, a):
    """Aturan kata kunci tambahan untuk makanan Indonesia; tingkat yang lebih tinggi selalu menang."""
    ada = lambda *k: any(re.search(r"\b" + re.escape(x), n) for x in k)
    naik = lambda lama, baru: baru if kb.L3.index(baru) > kb.L3.index(lama) else lama
    al = list(a["al"])
    if ada("tahu", "tempe", "oncom", "ketoprak", "gado", "pecel"): al.append("kedelai")
    if ada("kacang tanah", "gado", "pecel", "karedok", "ketoprak", "sate"): al.append("kacang tanah")
    if ada("gado"): al.append("telur")
    if ada("mi ayam", "mi gandum"): al.append("gluten")
    a["al"] = list(dict.fromkeys(al))
    if ada("sapi", "bakso", "rawon", "sate", "daging"): a["je"] = "hewani"
    if ada("gado") and a["je"] == "nabati": a["je"] = "telur_susu"
    for kunci, tinggi, sedang in (
            ("ig", ("nasi putih", "lontong", "ketupat", "bubur nasi", "bubur ayam", "mi ", "bihun", "ketoprak", "nasi padang"),
             ("nasi merah", "nasi jagung", "nasi gandum", "nasi tim", "ubi", "singkong", "talas", "sukun", "nangka", "sawo", "rambutan", "lengkeng", "duku", "labu kuning", "bubur kacang hijau")),
            ("na", ("soto", "rawon", "bakso", "mi ayam", "sate", "ketoprak"),
             ("tumis", "sup", "sayur asem", "sayur sop", "bening", "pepes", "gado", "pecel", "karedok", "capcay", "urap", "cah", "oseng", "orak", "geprek", "nasi padang", "bubur ayam", "nasi tim")),
            ("pu", ("sapi", "rawon", "bakso", "tongkol"),
             ("tahu", "tempe", "oncom", "kacang hijau", "kacang tanah", "ayam", "ikan", "daun singkong", "jamur", "soto", "sate", "seafood")),
            ("ko", ("sapi", "rawon", "bakso", "daging", "gado", "orak"), ("ayam", "geprek", "sate", "seafood"))):
        if ada(*tinggi): a[kunci] = naik(a[kunci], "tinggi")
        elif ada(*sedang): a[kunci] = naik(a[kunci], "sedang")
    if ada("asem", "markisa", "sirsak", "belimbing", "jeruk bali", "geprek", "manggis"): a["la"] = "iritatif"
    return a


# Perkiraan harga (Rupiah per kilogram makanan jadi) untuk makanan dasar yang tidak punya harga eksplisit.
# Tingkat: murah, sedang, mahal; dihitung per kategori. Bahan impor atau premium masuk tingkat mahal.
RATE = {"K": (22000, 35000, 70000), "P": (35000, 85000, 300000), "S": (25000, 45000, 100000), "B": (25000, 55000, 140000),
        "L": (120000, 250000, 400000), "H": (35000, 55000, 140000)}
MAHAL = ("salmon", "scallop", "sirloin", "steak", "trout", "cod", "sea bass", "haddock", "sarden", "makerel", "kalkun", "paella", "poke", "pistachio",
         "kenari", "almond", "blueberry", "raspberry", "blackberry", "ceri", "nektarin", "aprikot", "persik", "plum", "buah ara", "artichoke", "asparagus",
         "brussels", "swiss chard", "kale", "arugula", "couscous", "bulgur", "farro", "polenta", "quinoa", "soba", "sourdough", "rye", "risotto",
         "burrito", "nicoise", "yunani", "hummus", "kebab", "teriyaki", "shakshuka", "ratatouille", "tabbouleh", "granola", "cokelat", "chia", "pita",
         "tortilla", "beef stew", "tuna", "pasta", "wrap", "zucchini", "paprika", "artichoke")
MURAH = ("beras", "ubi", "kentang", "jagung", "telur", "tahu", "tofu", "tempe", "kacang", "pisang", "pepaya", "semangka", "melon", "wortel", "kubis",
         "buncis", "bayam", "terong", "selada", "timun", "oatmeal", "tilapia", "nanas", "jeruk", "mangga")


def _harga_perkiraan(f):
    n = f["nama"].lower()
    for kata, harga in {"alpukat": 6000, "popcorn": 3000}.items():  # harga khusus yang tidak cocok dengan tarif kategori
        if kata in n: return harga
    tingkat = 2 if any(x in n for x in MAHAL) else 0 if any(x in n for x in MURAH) else 1
    return max(1500, int(round(f["g"] * RATE[f["k"]][tingkat] / 1000 / 500)) * 500)


# Harga acuan hasil penelusuran web (Oktober 2026), Rupiah per porsi dataset; menimpa perkiraan tarif per kategori.
# Sumber bahan mentah: SP2KP Kemendag 6 Okt 2026 (ayam ras Rp40.174/kg, telur Rp26.795/kg, beras medium Rp14.027/kg, beras premium
# Rp15.689/kg, sapi paha belakang Rp144.166/kg); Panel Harga/PIHPS 5 Okt 2026 (ayam Rp41.000-47.000/kg, telur Rp29.500-31.800/kg, sapi
# Rp153.000/kg); Bapanas awal 2026 (ikan kembung Rp42.000-47.000/kg, tongkol Rp35.000-37.600/kg, bandeng Rp33.000-36.000/kg);
# Pasar Surabaya 20 Juli 2026 (tempe Rp6.000-14.500/kg, tahu Rp3.000-12.000/kg, apel Rp33.700/kg, jeruk Rp28.300/kg, pepaya Rp13.000/kg,
# pisang Rp22.500/kg, bayam/kangkung Rp1.800-2.300 per ikat). Harga warung: nasi sayur Rp4.000-6.000, soto Rp5.000-15.000,
# gado-gado sekitar Rp15.000, soto/bubur ayam Rp8.000-10.000, gorengan Rp2.000-3.000. Harga bergantung kota dan musim.
HARGA_WEB = {"nasi putih": 4500, "nasi merah": 5500, "apel": 6000, "pepaya": 3000, "jeruk": 3500, "pisang": 3000, "dada ayam panggang": 7500,
             "ayam bakar tanpa kulit": 9000, "ayam rebus tanpa kulit": 7500, "ikan kembung bakar": 8000, "ikan tongkol kukus": 6500,
             "daging sapi rebus tanpa lemak": 17000, "gado-gado": 15000, "soto ayam bening": 12000, "bubur ayam tanpa kerupuk": 11000,
             "telur rebus": 2000, "tempe panggang": 1500, "tahu kukus": 2000}


def _bangun(baris):
    k, nama, g, kkal, p, ka, l, s, en, *harga = baris.split("|")
    a = _tambah_id(nama.lower(), _atribut(nama.lower()))
    f = kb.frame(nama, KAT[k], f"{g} gram", float(kkal), float(p), float(ka), float(l), float(s), ig=a["ig"], na=a["na"],
                 pu=a["pu"], ko=a["ko"], la=a["la"], je=a["je"], al=a["al"])
    f["k"], f["bahan"], f["g"], f["en"] = k, [], float(g), en
    f["harga"] = HARGA_WEB.get(nama.lower()) or (int(harga[0]) if harga else _harga_perkiraan(f))  # Rupiah per porsi dataset
    f["alasan"], f["saran"] = penjelasan.untuk(f)
    return f


DATASET = [_bangun(b) for b in (BARIS + BARIS_ID).splitlines() if b.strip()]
# Normalisasi harga per porsi agar tidak melonjak untuk bahan yang sama-sama porsi kecil.
for _f in DATASET:
    _nama = _f["nama"].lower()
    _gram = float(_f.get("g", 100))
    _harga = int(_f.get("harga", 0) or 0)
    if _gram <= 150 and _harga > 18000:
        _f["harga"] = 15000
    elif _gram <= 250 and _harga > 22000:
        _f["harga"] = 18000
    elif _gram > 250 and _harga > 26000:
        _f["harga"] = 22000
assert len(DATASET) >= 200, f"dataset dasar terlalu sedikit: {len(DATASET)}"
DASAR = len(DATASET)
KENYANG = {"tinggi": 2, "sedang": 1, "rendah": 0}


SARAPAN_K = ("oatmeal", "roti gandum", "roti rye", "roti sourdough", "ubi jalar", "jagung", "kentang rebus", "granola", "polenta", "pita", "tortilla")
SARAPAN_P = ("telur rebus", "telur puyuh", "putih telur", "yogurt", "susu", "keju cottage", "tofu", "edamame", "hummus")
SARAPAN_H = ("omelet", "scrambled", "shakshuka", "tofu scramble")
BUKAN_UTAMA_K = ("oatmeal", "roti", "granola", "pita", "tortilla")
BUKAN_UTAMA_P = ("yogurt", "susu", "keju", "putih telur", "telur puyuh", "hummus")
CAMILAN_P = ("yogurt", "susu", "keju cottage", "telur puyuh", "edamame", "kacang polong", "hummus", "kacang arab")
CAMILAN_L = ("alpukat", "almond", "kenari", "popcorn", "mete", "pistachio", "biji", "cokelat")

# tambahan untuk makanan Indonesia
SARAPAN_K += ("ubi ungu", "ubi cilembu", "singkong", "talas", "bubur nasi", "lontong", "sukun", "nasi jagung")
SARAPAN_P += ("tahu kukus", "tempe panggang", "oncom", "bubur kacang hijau", "kacang hijau rebus")
SARAPAN_H += ("orak-arik", "bubur ayam")
BUKAN_UTAMA_K += ("ubi ungu", "ubi cilembu", "singkong", "talas", "sukun", "bubur nasi")
BUKAN_UTAMA_P += ("bubur kacang hijau", "kacang tanah", "kacang hijau rebus")
CAMILAN_P += ("tahu kukus", "tempe panggang", "oncom", "kacang hijau rebus", "bubur kacang hijau", "kacang tanah")
CAMILAN_L += ("biji labu", "bunga matahari", "kelapa")

# (id, waktu, judul, porsi dari kalori harian): pengguna mencentang waktu makan yang diinginkan (lihat kb.SLOT_MENU).
SLOT = [(i, waktu, nama, bagi) for i, nama, waktu, bagi in kb.SLOT_MENU]
BASIS = ("nama", "kkal", "protein", "karbo", "lemak", "serat")
slug = lambda n: re.sub(r"\W+", "_", n.lower()).strip("_")
BY_SLUG = {slug(f["nama"]): f for f in DATASET}
assert len(BY_SLUG) == len(DATASET), "ada nama makanan ganda"


def _sebut(f, skala):
    """Porsi yang ditampilkan: kelipatan 0,25 porsi dataset beserta gramnya."""
    kata = {.5: "½", 1: "1", 1.5: "1½", 2: "2"}.get(skala) or f"{skala:g}".replace(".", ",")
    return f"{kata} porsi · ±{round(f['g'] * skala / 5) * 5:g} gram"


def _harga(f, skala):
    """Harga porsi yang ditampilkan (Rupiah, kelipatan 500). 0 jika harga belum diketahui."""
    return max(500, int(round(f["harga"] * skala / 500)) * 500) if f.get("harga") else 0


def _item(f, skala):
    return dict(slug=slug(f["nama"]), nama=f["nama"], kat=f["kat"], porsi=_sebut(f, skala), skala=skala,
                harga=_harga(f, skala), alasan=f.get("alasan", ""), saran=f.get("saran", ""),
                **{x: round(f[x] * skala, 1) for x in BASIS[1:]})


def _skala(base, target, lo=.5, hi=1.75):
    return min(hi, max(lo, round(target / base * 4) / 4)) if base else 1


def _pilih(rng, kandidat, pakai, ideal=None, banyak=4):
    """Dari kandidat (urut: paling mengenyangkan / paling dekat kalori ideal), pilih acak dari beberapa teratas; hindari pengulangan."""
    c = [f for f in kandidat if f["nama"] not in pakai] or kandidat
    if not c: return None
    mode = getattr(rng, "mode", None)  # "murah" / "mahal": dipakai untuk menghitung biaya minimum dan maksimum
    if mode:
        c = sorted(c, key=lambda f: (f["harga"] / max(f["kkal"], 40)) * (1 if mode == "murah" else -1))[:3]
    else:
        c = sorted(c, key=lambda f: -KENYANG[f["kenyang"]] * 2 + (abs(f["kkal"] - ideal) / 60 if ideal else 0))[:banyak]
    f = rng.choice(c)
    pakai.add(f["nama"])
    return f


def _slot_utama(p, aman, rng, pakai, sid, target):
    ada = lambda f, daftar: any(x in f["nama"].lower() for x in daftar)
    pool = lambda kat, ok=lambda f: True: [f for f in aman if f["k"] == kat and ok(f)]
    if sid == "sarapan":
        h = _pilih(rng, pool("H", lambda f: ada(f, SARAPAN_H)), pakai) if rng.random() < .35 else None
        if h:
            kom = [h, _pilih(rng, pool("B"), pakai)]
        else:
            kom = [_pilih(rng, pool("K", lambda f: ada(f, SARAPAN_K)), pakai), _pilih(rng, pool("P", lambda f: ada(f, SARAPAN_P)), pakai),
                   _pilih(rng, pool("B"), pakai)]
    else:
        utama_k = pool("K", lambda f: not ada(f, BUKAN_UTAMA_K))
        utama_p = pool("P", lambda f: not ada(f, BUKAN_UTAMA_P))
        h = _pilih(rng, pool("H", lambda f: not ada(f, SARAPAN_H) and f["kkal"] <= 500), pakai) if rng.random() < .4 else None
        if h:  # hidangan lengkap; tambah karbohidrat hanya jika hidangannya belum mengandung banyak karbohidrat
            kom = [h] + ([] if h["karbo"] >= 35 else [_pilih(rng, utama_k, pakai)]) + [_pilih(rng, pool("S"), pakai)]
        else:
            kom = [_pilih(rng, utama_k, pakai), _pilih(rng, utama_p, pakai), _pilih(rng, pool("S"), pakai)]
        if sid == "siang": kom.append(_pilih(rng, pool("B"), pakai))
    kom = [f for f in kom if f]
    skala = _skala(sum(f["kkal"] for f in kom), target)
    return [_item(f, skala) for f in kom]


def _slot_camilan(p, aman, rng, pakai, sid, target):
    ada = lambda f, daftar: any(x in f["nama"].lower() for x in daftar)
    buah = [f for f in aman if f["k"] == "B"]
    prot = [f for f in aman if f["k"] in "PL" and ada(f, CAMILAN_P)]
    lemak = [f for f in aman if f["k"] == "L" and ada(f, CAMILAN_L)]
    kand = {"camilan1": buah + lemak, "camilan2": prot + lemak, "camilan3": prot}.get(sid) or buah
    kand = [f for f in kand if f["nama"] not in pakai] or kand
    mode = getattr(rng, "mode", None)
    if mode: kand = sorted(kand, key=lambda f: f["harga"] * _skala(f["kkal"], target, .5, 1.5) * (1 if mode == "murah" else -1))[:3]
    else: kand = sorted(kand, key=lambda f: abs(f["kkal"] * _skala(f["kkal"], target, .5, 1.5) - target))[:5]
    if not kand: return []
    f = rng.choice(kand)
    pakai.add(f["nama"])
    return [_item(f, _skala(f["kkal"], target, .5, 1.5))]


class _Acak(random.Random):
    """Pengacak dengan atribut mode ("murah"/"mahal"/None) yang dibaca _pilih dan _slot_camilan."""
    mode = None


def pilihan_slot(p):
    """Daftar id waktu makan yang dicentang pengguna (urut hari); kosong/tidak valid -> semua."""
    dipilih = [i for i in kb.SLOT_ID if i in (p.get("slot") or [])]
    return dipilih or list(kb.SLOT_ID)


def susun_jadwal(p, h, seed=None, mode=None):
    """Jadwal makan harian dari dataset: hanya untuk waktu makan yang dicentang, disaring dengan aturan profil, porsi diatur agar kalori
    tiap waktu makan mendekati bagiannya dari target harian. mode="murah"/"mahal" dipakai untuk mencari biaya minimum/maksimum."""
    rng, pakai = _Acak(seed), set()
    rng.mode = mode
    aman = [f for f in DATASET if not f.get("web") and not kb.lolos(p, f)]
    dipilih, baris = pilihan_slot(p), []
    for sid, waktu, judul, bagi in SLOT:
        if sid not in dipilih: continue
        target = h["kal"] * bagi
        items = (_slot_camilan if sid.startswith("camilan") else _slot_utama)(p, aman, rng, pakai, sid, target)
        if items:
            baris.append(dict(id=sid, waktu=waktu, judul=judul, makan=True, items=items,
                              kkal=round(sum(i["kkal"] for i in items)), protein=round(sum(i["protein"] for i in items)),
                              karbo=round(sum(i["karbo"] for i in items)), lemak=round(sum(i["lemak"] for i in items)),
                              serat=round(sum(i["serat"] for i in items)), harga=sum(i["harga"] for i in items)))
    tot = {x: sum(b[x] for b in baris) for x in ("kkal", "protein", "karbo", "lemak", "serat", "harga")}
    return dict(baris=baris, total=tot, persen=round(tot["kkal"] / h["kal"] * 100) if h["kal"] else 0)


# ---------------------------------------------------------------- biaya
_RENTANG = {}
_SEED_BIAYA = range(1, 41)


def rentang_biaya(p, h):
    """(minimum, maksimum) biaya per hari (Rupiah) untuk waktu makan yang dipilih, setelah alergi/preferensi/tidak suka disaring.
    Dicari dengan menyusun 40 jadwal 'termurah' dan 40 jadwal 'termahal' lalu mengambil yang paling kecil / paling besar."""
    kunci = (tuple(pilihan_slot(p)), tuple(p.get("alergi", [])), p.get("tidak_suka", ""), p.get("pref"), h["kal"])
    if kunci not in _RENTANG:
        murah = [susun_jadwal(p, h, s, "murah")["total"]["harga"] for s in _SEED_BIAYA]
        mahal = [susun_jadwal(p, h, s, "mahal")["total"]["harga"] for s in _SEED_BIAYA]
        lo, hi = min(murah), max(mahal)
        _RENTANG[kunci] = (-(-lo // 500) * 500, max(-(-hi // 500) * 500, -(-lo // 500) * 500))
    return _RENTANG[kunci]


def rupiah(x):
    return "Rp " + f"{int(x):,}".replace(",", ".")


def masalah_biaya(p, h):
    """Pemeriksaan biaya. Jika tidak kosong, jadwal TIDAK ditampilkan dan pengguna diminta mengganti biaya di profil."""
    nama = ", ".join(kb.SLOT_NAMA[i].lower() for i in pilihan_slot(p))
    lo, hi = rentang_biaya(p, h)
    if hi == 0:
        return [f"Tidak ada menu yang cocok untuk {nama} dengan alergi, preferensi, dan makanan tidak disukai yang kamu pilih. Silakan kurangi pilihan di profil."]
    if p.get("biaya", 0) < lo:
        return [f"Biaya yang kamu isi ({rupiah(p['biaya'])} per hari) kurang untuk menu yang dipilih ({nama}). "
                f"Biaya minimum: {rupiah(lo)} per hari dan biaya maksimum: {rupiah(hi)} per hari. Silakan ganti biaya di profil."]
    return []


def susun_jadwal_biaya(p, h, seed):
    """Jadwal acak (sesuai seed) yang total biayanya tidak melebihi biaya pengguna. Jika acak tidak ketemu, pakai susunan termurah."""
    biaya = p.get("biaya") or 10 ** 9
    for i in range(30):
        j = susun_jadwal(p, h, seed + i * 7919)
        if j["total"]["harga"] <= biaya: return j
    for i in range(40):  # biaya ketat: pilih yang murah, tetapi tetap bervariasi mengikuti seed agar "Menu lain" berganti menu
        j = susun_jadwal(p, h, seed + i * 104729, "murah")
        if j["total"]["harga"] <= biaya: return j
    for s in _SEED_BIAYA:  # pengaman: susunan termurah yang diketahui (selalu <= biaya minimum yang dilaporkan rentang_biaya)
        j = susun_jadwal(p, h, s, "murah")
        if j["total"]["harga"] <= biaya: return j
    return susun_jadwal(p, h, 1, "murah")


# ---------------------------------------------------------------- makanan tambahan dari web
BERKAS_WEB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dataset_web.json")
_kunci_web = threading.Lock()


def _frame_web(e):
    """Bangun frame dari entri dataset_web.json (nilai per 100 g). Kategori 'W' dan web=True: tidak dipakai menyusun jadwal."""
    f = kb.frame(e["nama"], "Data dari web (belum diverifikasi)", "100 gram", float(e["kkal"]), float(e["protein"]), float(e["karbo"]),
                 float(e["lemak"]), float(e["serat"]))
    f.update(k="W", bahan=[], g=100.0, en=e.get("en") or e["nama"], harga=0, web=True, sumber=e.get("sumber", "web"),
             deskripsi=e.get("deskripsi", ""), alasan=e.get("deskripsi", ""), saran="")
    return f


def _muat_web():
    try:
        with open(BERKAS_WEB, encoding="utf-8") as fh: data = json.load(fh)
    except (OSError, ValueError):
        return
    for e in data if isinstance(data, list) else []:
        try: f = _frame_web(e)
        except (KeyError, TypeError, ValueError): continue
        if slug(f["nama"]) not in BY_SLUG:
            DATASET.append(f)
            BY_SLUG[slug(f["nama"])] = f


def tambah_web(e):
    """Tambahkan makanan hasil penelusuran web ke dataset (memori + dataset_web.json). Mengembalikan frame, atau None jika sudah ada."""
    with _kunci_web:
        f = _frame_web(e)
        if slug(f["nama"]) in BY_SLUG: return None
        try:
            with open(BERKAS_WEB, encoding="utf-8") as fh: data = json.load(fh)
        except (OSError, ValueError):
            data = []
        data.append({k: e.get(k) for k in ("nama", "kkal", "protein", "karbo", "lemak", "serat", "en", "sumber", "deskripsi")})
        with open(BERKAS_WEB + ".tmp", "w", encoding="utf-8") as fh: json.dump(data, fh, ensure_ascii=False, indent=1)
        os.replace(BERKAS_WEB + ".tmp", BERKAS_WEB)
        DATASET.append(f)
        BY_SLUG[slug(f["nama"])] = f
        return f


_muat_web()
