"""Original editorial recipes. Photos are licensed reference photos, not claimed cooking results."""
PHOTO_LICENSE = 'https://www.pexels.com/license/'
RECIPES = [
    dict(id='chicken-broccoli', title='鶏むね肉とブロッコリーのライスボウル', subtitle='シンプルに、しっかり満たす。', goal='muscle', minutes=20, servings=1, protein_source='鶏むね肉', tags=['鶏むね肉', 'ブロッコリー', 'ごはん', '作り置き'],
         ingredients=[['鶏むね肉（皮なし）', '150g'], ['ブロッコリー', '100g'], ['温かいごはん', '150g'], ['オリーブオイル', '小さじ1'], ['しょうゆ', '小さじ1'], ['レモン汁', '小さじ1'], ['塩・こしょう', '少々']],
         steps=['鶏むね肉を均等な厚さの一口大に切り、塩・こしょうを振る。生肉に触れた器具は洗う。', 'ブロッコリーを小房に分け、沸騰した湯で3〜4分ゆでる。', 'フライパンに油を熱し、鶏肉を両面焼く。ふたをして加熱し、中心まで十分に火を通す（中心温度75℃で1分以上が目安）。', 'しょうゆとレモン汁を絡め、ごはんとブロッコリーと一緒に盛る。'],
         tip='筋トレ後の食事にも。主食の量は、その日の活動量や他の食事に合わせて調整できます。', allergy=['大豆', '小麦', '鶏肉'], photo='chicken.jpg', photographer='IARA MELO', photo_url='https://www.pexels.com/photo/healthy-meal-prep-with-chicken-and-broccoli-30635713/'),
    dict(id='salmon-vegetables', title='鮭と彩り野菜のレモンソテー', subtitle='素材のうまみで、軽やかに。', goal='diet', minutes=20, servings=1, protein_source='鮭', tags=['鮭', 'サーモン', 'ズッキーニ', 'パプリカ', '魚'],
         ingredients=[['生鮭', '1切れ（約120g）'], ['ズッキーニ', '1/3本'], ['パプリカ', '1/4個'], ['ミニトマト', '4個'], ['レモン汁', '小さじ2'], ['オリーブオイル', '小さじ1'], ['塩・こしょう', '少々']],
         steps=['野菜を洗って食べやすい大きさに切る。鮭の水気を拭き、塩・こしょうを振る。', 'フライパンに油を熱し、鮭を皮側から焼く。裏返し、野菜を加える。', '水大さじ1を加えてふたをし、弱めの中火で5〜7分を目安に、鮭の中心まで十分に火を通す。', 'ふたを取って余分な水分を飛ばし、レモン汁を回しかけて盛る。'],
         tip='ソースを足しすぎず、レモンの酸味で満足感を。必要に応じてごはんなどの主食を添えてください。', allergy=['さけ'], photo='salmon.jpg', photographer='Daniela Elena Tentis', photo_url='https://www.pexels.com/photo/cooked-meat-with-vegetables-725991/'),
    dict(id='crispy-tofu', title='木綿豆腐のカリッとオーブン焼き', subtitle='植物性のたんぱく質を、いつもの食卓に。', goal='diet', minutes=35, servings=1, protein_source='木綿豆腐', tags=['豆腐', '木綿豆腐', '大豆', 'オーブン', 'ベジタリアン'],
         ingredients=[['木綿豆腐', '200g'], ['片栗粉', '小さじ2'], ['しょうゆ', '小さじ1'], ['ごま油', '小さじ1'], ['おろししょうが', '小さじ1/2'], ['こしょう', '少々']],
         steps=['豆腐をキッチンペーパーで包み、重しをして10分ほど水切りする。オーブンを200℃に予熱する。', '豆腐を約2cm角に切り、しょうゆ・ごま油・しょうが・こしょうで和える。', '片栗粉を薄くまぶし、クッキングシートを敷いた天板に、間隔をあけて並べる。', '200℃で約20分、途中で一度返し、表面が香ばしくなるまで焼く。加熱時間は機器に合わせて調整する。'],
         tip='主菜として野菜や主食と組み合わせるほか、サラダのトッピングにも。', allergy=['大豆', '小麦', 'ごま'], photo='tofu.jpg', photographer='Alesia Kozik', photo_url='https://www.pexels.com/photo/a-close-up-shot-of-cooked-tofu-6120243/'),
    dict(id='tuna-egg-salad', title='ツナと卵・ひよこ豆のサラダ', subtitle='ひと皿に、たんぱく質と彩りを。', goal='muscle', minutes=15, servings=1, protein_source='ツナ・卵・ひよこ豆', tags=['ツナ', '卵', 'ひよこ豆', 'レタス', 'サラダ'],
         ingredients=[['水煮ツナ', '1缶（約70g）'], ['卵', '1個'], ['ゆでひよこ豆', '50g'], ['さやいんげん', '40g'], ['レタス', '2枚'], ['オリーブオイル', '小さじ1'], ['酢', '小さじ2'], ['塩・こしょう', '少々']],
         steps=['卵を沸騰した湯で10〜12分ゆでて冷まし、殻をむいて食べやすく切る。', 'さやいんげんを3〜4分ゆでる。レタスをよく洗って水気を切る。', '水気を切ったツナ・ひよこ豆・野菜を器に入れる。', '油・酢・塩・こしょうを混ぜて和え、卵をのせる。'],
         tip='主食を添えれば食事として、主食を別にとる日はおかずとして使えます。', allergy=['卵'], photo='salad.jpg', photographer='Alesia Kozik', photo_url='https://www.pexels.com/photo/tuna-and-green-bean-salad-with-egg-in-bowl-6544221/'),
    dict(id='yogurt-oats', title='ギリシャヨーグルトとベリーのオーツボウル', subtitle='忙しい朝も、自分を整える5分。', goal='muscle', minutes=5, servings=1, protein_source='ギリシャヨーグルト', tags=['ヨーグルト', 'ギリシャヨーグルト', 'オートミール', 'ベリー', '朝食'],
         ingredients=[['無糖ギリシャヨーグルト', '200g'], ['そのまま食べられるオートミール', '30g'], ['冷凍または生のベリー', '50g'], ['くるみ', '10g'], ['はちみつ（任意）', '小さじ1']],
         steps=['ベリーは表示に従って解凍し、くるみは食べやすく砕く。', '器にヨーグルトと、そのまま食べられる表示のオートミールを入れて混ぜる。加熱が必要な製品は表示通り調理し、冷ましてから使う。', 'ベリーとくるみをのせ、好みではちみつを少量かける。'],
         tip='甘さは果物を活用。乳製品・ナッツにアレルギーがある場合は別のレシピを選んでください。はちみつは1歳未満に与えないでください。', allergy=['乳', 'くるみ'], photo='yogurt.jpg', photographer='Micheile Henderson', photo_url='https://www.pexels.com/photo/clear-glass-cup-with-ice-cream-and-black-berries-7727477/'),
]
for _recipe in RECIPES:
    _recipe.update(photo_kind='reference', license_url=PHOTO_LICENSE, generated=False, published=True, user_id=None)
