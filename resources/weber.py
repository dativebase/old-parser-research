import codecs

key = dict(
    gls = u'\u0294',
    pah = u'\u02B0',
    vcl = u'\u0325',
    lng = u'\u02D0',
    sci = u'\u026A',
    sch = u'\u0259',
    acu = u'\u0301',
    crc = u'\u0302',
    sus = u'\u02E2',
    pstr = u'\u02C8',
    eps = u'\u025B',
    omo = u'\u0254',
    ncnb = u'\u028A'
)

forms = (
    (
        u'i.to{vcl}.{pah}ko{acu}{lng}.n{sci}m.{gls}a{vcl}'.format(**key),
        u"itohko{acu}o{acu}nim'a".format(**key),
        u'it-ohkoon-i-m-wa',
        u'LOC-find-TI-DIR-3SG',
        u'She found it then.',
        u'sent'
    ),
    (
        u'oo{vcl}.{pah}ko{acu}{lng}.n{sci}t'.format(**key),
        u'oohko{acu}o{acu}nit'.format(**key),
        u'ohkoon-i-t',
        u'find-TI-IMP',
        u'Find it!',
        u'sent'
    ),
    (
        u'i.to{acu}o{vcl}.{pah}ko.yi{lng}'.format(**key),
        u'ito{acu}o{acu}hkoyii'.format(**key),
        u'it-yoohko-yii-wa',
        u'LOC-wait-DIR-3SG',
        u'She waited for him.',
        u'sent'
    ),
    (
        u'oo{vcl}.{pah}ko{acu}{lng}s'.format(**key),
        u'oohko{acu}o{acu}s'.format(**key),
        u'yoohko-s',
        u'wait-IMP',
        u'Wait for him!',
        u'sent'
    ),
    (
        u'i.p{sch}{acu}s.ka'.format(**key),
        u'ipa{acu}ska'.format(**key),
        u'ipa{acu}sskaa-wa'.format(**key),
        u'dance-3SG',
        u'He danced.',
        u'sent'
    ),
    (
        u'i.ks.ki{acu}.ma'.format(**key),
        u'ikski{acu}ma'.format(**key),
        u'ikskimaa-wa',
        u'dance-3SG',
        u'She hunted.',
        u'sent'
    ),
    (
        u'ii{vcl}.{pah}ki{acu}{lng}.ta'.format(**key),
        u'iihki{acu}i{acu}ta'.format(**key),
        u'ihkiitaa-wa',
        u'bake-3SG',
        u'He baked.',
        u'sent'
    ),
    (
        u'ii{vcl}.{pah}ki{acu}{lng}.ta{lng}t'.format(**key),
        u'iihki{acu}i{acu}taat'.format(**key),
        u'ihkiitaa-t',
        u'bake-IMP',
        u'Bake!',
        u'sent'
    ),
    (
        u'ii{vcl}.{pah}ki{acu}{lng}.ta{lng}n'.format(**key),
        u'iihki{acu}i{acu}taan'.format(**key),
        u'ihkiitaa-n-wa',
        u'bake-NOM-PROX.SG',
        u'baking',
        u'N'
    ),
    (
        u'i.si{crc}{gls}.ka.t{sus}i'.format(**key),
        u"isi{acu}'katsi".format(**key),
        u"si'kat-yii-wa",
        u'kick-DIR-3SG',
        u'He kicked him.',
        u'sent'
    ),
    (
        u'in.{gls}{sci}{vcl}.{pah}ki{crc}'.format(**key),
        u'inihki{acu}'.format(**key),
        u'inihki-wa',
        u'sing-3SG',
        u'He sang.',
        u'sent'
    ),
    (
        u'in.{gls}{sci}{vcl}.{pstr}{pah}ki'.format(**key),
        u'inihki{acu}'.format(**key),
        u'inihki-wa',
        u'sing-3SG',
        u'He sang.',
        u'sent'
    ),
    (
        u'{eps}{acu}{lng}.ps.t{sus}o.j{sci}'.format(**key),
        u'a{acu}i{acu}pstsoyi'.format(**key),
        u'a{acu}-ipsst-ooyi-wa'.format(**key),
        u'IMPF-inside-eat-3SG',
        u'She eats inside.',
        u'sent'
    ),
    (
        u'{omo}{acu}{lng}.o.j{sci}'.format(**key),
        u'a{acu}o{acu}oyi'.format(**key),
        u'a{acu}-ooyi-wa'.format(**key),
        u'IMPF-eat-3SG',
        u'He is eating.',
        u'sent'
    ),
    (
        u'{omo}{acu}{lng}.o.wa.t{sus}i'.format(**key),
        u'a{acu}o{acu}owatsi'.format(**key),
        u'a{acu}-oowat-yii-wa'.format(**key),
        u'IMPF-eat-DIR-3SG',
        u'He is eating it.',
        u'sent'
    ),
    (
        u'{omo}{acu}{lng}.o.wa.to{lng}.ma{vcl}'.format(**key),
        u'a{acu}o{acu}owatooma'.format(**key),
        u'a{acu}-oowatoo-m-wa'.format(**key),
        u'IMPF-eat-DIR-3SG',
        u'He is eating it.',
        u'sent'
    ),
    (
        u'pi{acu}{lng}t'.format(**key),
        u'pi{acu}i{acu}t'.format(**key),
        u'ipii-t',
        u'enter-IMP',
        u'Enter!',
        u'sent'
    ),
    (
        u'i.pi{acu}{lng}.ma{vcl}'.format(**key),
        u'ipi{acu}i{acu}ma'.format(**key),
        u'ipii-m-wa',
        u'enter-DIR-3SG',
        u'He entered it.',
        u'sent'
    ),
    (
        u'i.pi.k{sus}i{crc}'.format(**key),
        u'ipiksi{acu}'.format(**key),
        u'ipiksi-wa',
        u'hit-3SG',
        u'He hit.',
        u'sent'
    ),
    (
        u'i.ka{acu}{gls}.kja{lng}.ki'.format(**key),
        u"ika{acu}'kiaaki".format(**key),
        u"ika'kiaaki-wa",
        u'chop-3SG',
        u'He chopped wood.',
        u'sent'
    ),
    (
        u'i.ka{crc}{gls}.kja{lng}.ki'.format(**key),
        u"ika{acu}'kiaaki".format(**key),
        u"ika'kiaaki-wa",
        u'chop-3SG',
        u'He chopped wood.',
        u'sent'
    ),
    (
        u'i.t{sus}{sci}.ni{acu}.ki'.format(**key),
        u'itsini{acu}ki'.format(**key),
        u'itsiniki-wa',
        u'recount-3SG',
        u'She told a story.',
        u'sent'
    ),
    (
        u'i.ji{acu}{lng}.t{sus}{sci}t.t{sus}{sci}.ma'.format(**key),
        u'iyi{acu}i{acu}tsittsima'.format(**key),
        u'yiitsittsimaa-wa',
        u'slice.meat.thinly-3SG',
        u'She sliced meat thinly.',
        u'sent'
    ),
    (
        u'i.s{sci}.mi{acu}m.{gls}o{vcl}.{pah}ki'.format(**key),
        u"isimi{acu}m'ohki".format(**key),
        u'simimmohki-wa',
        u'gossip-3SG',
        u'He gossiped.',
        u'sent'
    ),
    (
        u'i.yi{acu}'.format(**key),
        u'iyi{acu}'.format(**key),
        u'ooyi-wa',
        u'eat-3SG',
        u'She ate.',
        u'sent'
    ),
    (
        u's{sci}.mi{acu}t'.format(**key),
        u'simi{acu}t'.format(**key),
        u'simi-t',
        u'drink-IMP',
        u'Drink!',
        u'sent'
    ),
    (
        u'o.ka{acu}{lng}t'.format(**key),
        u'oka{acu}a{acu}t'.format(**key),
        u'okaa-t',
        u'rope-IMP',
        u'Rope!',
        u'sent'
    ),
    (
        u'ma{gls}.t{sus}i{acu}t'.format(**key),
        u"ma'tsi{acu}t".format(**key),
        u"ma'tsi-t",
        u'take-IMP',
        u'Take it!',
        u'sent'
    ),
    (
        u'o{gls}.ka{acu}{lng}t'.format(**key),
        u"o'ka{acu}a{acu}t".format(**key),
        u"yo'kaa-t",
        u'sleep-IMPF',
        u'Sleep!',
        u'sent'
    ),
    (
        u'oo{vcl}.{pah}ki{acu}t'.format(**key),
        u'oohki{acu}t'.format(**key),
        u'ohki-t',
        u'bark-IMP',
        u'Bark!',
        u'sent'
    ),
    (
        u'ii{vcl}.{pah}p{ncnb}{acu}m.ma.t{sus}i'.format(**key),
        u'iihpo{acu}mmatsi'.format(**key),
        u'ohpomm-at-yii-wa',
        u'buy-TA-DIR-3SG',
        u'He bought her.',
        u'sent'
    ),
    (
        u'i{gls}.na{acu}{lng}.ki'.format(**key),
        u"i'na{acu}a{acu}ki".format(**key),
        u"i'naaki-wa",
        u'be.thirsty-3SG',
        u'He thirsted.',
        u'sent'
    ),
    (
        u'ka{gls}.kja{acu}{lng}.k{sus}{sci}n'.format(**key),
        u"ka'kia{acu}a{acu}ksin".format(**key),
        u"ika'kiaaki-hsin",
        u'chop-NOM',
        u'firewood',
        u'N'
    ),
    (
        u'{sci}s.p{ncnb}{acu}m.{gls}{sci}{vcl}.{pah}ta'.format(**key),
        u"ispo{acu}m'ihta".format(**key),
        u'sspommihtaa-wa',
        u'help.out-3SG',
        u'She helped out.',
        u'sent'
    ),
    (
        u'i.ja{acu}{lng}.k{sci}{vcl}.{pah}ta'.format(**key),
        u'iya{acu}a{acu}kihta'.format(**key),
        u'ya{acu}akihtaa-wa'.format(**key),
        u'pack-3SG',
        u'She packed.',
        u'sent'
    ),
    (
        u'i.k{sch}{acu}n.{gls}{sci}{vcl}.{pah}ko.ji'.format(**key),
        u"ika{acu}n'ihkoyi".format(**key),
        u"ikanihko-yii-wa",
        u'hit-DIR-3SG',
        u'He hit.',
        u'sent'
    ),
    (
        u'{sci}s.s{sci}{acu}m.{gls}{sci}{vcl}.{pah}ka'.format(**key),
        u"issi{acu}m'ihka".format(**key),
        u'ssi{acu}mihkaa-wa'.format(**key),
        u'sniff-3SG',
        u'She sniffed.',
        u'sent'
    ),
    (
        u'i.po.wa{acu}{lng}'.format(**key),
        u'ipowa{acu}a{acu}'.format(**key),
        u'ipowaa-wa',
        u'arise-3SG',
        u'She got up.',
        u'sent'
    ),
    (
        u'a.wa.ja{acu}.ki'.format(**key),
        u'awaya{acu}ki'.format(**key),
        u'waawaya{acu}ki-yii-wa'.format(**key),
        u'beat-DIR-3SG',
        u'She hit him.',
        u'sent'
    ),
    (
        u'a.t{sus}{sci}.ni{acu}.ks{sci}n'.format(**key),
        u'atsini{acu}ksin'.format(**key),
        u'itsiniki-hsin',
        u'recount-NOM',
        u'story',
        u'N'
    ),
    (
        u'a.ko{vcl}.{pah}si{acu}.ma{lng}t'.format(**key),
        u'akohsi{acu}maat'.format(**key),
        u'waakohs-imaa-t',
        u'boil-AI-IMP',
        u'Boil it!',
        u'sent'
    ),
    (
        u'{sci}{sus}t.ta.yi{acu}'.format(**key),
        u'isttayi{acu}'.format(**key),
        u'isttayi-wa',
        u'dive-3SG',
        u'She dove.',
        u'sent'
    ),
    (
        u"ma{gls}.ta.ki{acu}t".format(**key),
        u"ma'taki{acu}t".format(**key),
        u"ma'taaki-t",
        u"take-IMP",
        u"Take it!",
        u"sent"
    ),
    (
        u'aw.{gls}a{vcl}.{pah}ka{acu}{lng}n'.format(**key),
        u"aw'ahka{acu}a{acu}n".format(**key),
        u'waawahkaa-n',
        u'walk-NOM',
        u'playing',
        u'N'
    ),
    (
        u'i{gls}.p{sci}.{sus}to{acu}.t{sus}{sci}m.{gls}a{vcl}'.format(**key),
        u"i'pisto{acu}tsim'a".format(**key),
        u"i'pistotsi-m-wa",
        u"wet-DIR-3SG",
        u"She wet it.",
        u"sent"
    ),
    (
        u"i.si{acu}.ks.ta.ki".format(**key),
        u"isi{acu}kstaki".format(**key),
        u"sikstaki-wa",
        u"bite-3SG",
        u"He bit.",
        u"sent"
    ),
    (
        u"a{gls}.po{acu}{gls}.ta.ki".format(**key),
        u"a'po{acu}'taki".format(**key),
        u"a'p-o't-aki-wa",
        u"about-grasp-AI-3SG",
        u"She worked.",
        u"sent"
    ),
    (
        u"a.s{sci}.m{sci}{acu}m.{gls}o{vcl}.{pah}ksin".format(**key),
        u"asimi{acu}m'ohksin".format(**key),
        u"simimmohki-hsin",
        u"gossip-NOM",
        u"gossiping",
        u"N"
    ),
    (
        u"a{acu}{lng}.ni{lng}".format(**key),
        u"a{acu}a{acu}nii".format(**key),
        u"waanii-wa",
        u"say-3SG",
        u"He said something.",
        u"sent"
    ),
    (
        u"a.ni{acu}{lng}t".format(**key),
        u"ani{acu}i{acu}t".format(**key),
        u"waanii-t",
        u"say-IMP",
        u"Say something!",
        u"sent"
    ),
    (
        u"a.ni{acu}s.s{sci}n".format(**key),
        u"ani{acu}ssin".format(**key),
        u"waanii-hsin",
        u"say-NOM",
        u"saying",
        u"N"
    ),
    (
        u"a{acu}{lng}.se{gls}.ni".format(**key),
        u"a{acu}a{acu}sai'ni".format(**key),
        u"waasai'ni-wa",
        u"cry-3SG",
        u"He cried.",
        u"sent"
    ),
    (
        u"a.se{acu}{gls}.n{sci}t".format(**key),
        u"asa{acu}i{acu}'nit".format(**key),
        u"waasai'ni-t",
        u"cry-IMP",
        u"Cry!",
        u"sent"
    ),
    (
        u"a.se{acu}n.{gls}s{sci}n".format(**key),
        u"asa{acu}i{acu}n'sin".format(**key),
        u"waasai'ni-hsin",
        u"cry-NOM",
        u"cry-baby",
        u"N"
    ),
    (
        u"a{acu}w.{gls}a{vcl}.{pah}ka".format(**key),
        u"a{acu}w'ahka".format(**key),
        u"waawahkaa-wa",
        u"walk-3SG",
        u"He walked.",
        u"sent"
    ),
    (
        u'aw.{gls}a{vcl}.{pah}ka{acu}{lng}t'.format(**key),
        u"aw'ahka{acu}a{acu}t".format(**key),
        u'waawahkaa-t',
        u'walk-IMP',
        u'Walk!',
        u'sent'
    ),
    (
        u"a{acu}{lng}.ko{vcl}.{pah}s{sci}m".format(**key),
        u"a{acu}a{acu}kohsim".format(**key),
        u"waakohs-i-m-wa",
        u"boil-TI-DIR-3SG",
        u"She boiled it.",
        u"sent"
    ),
    (
        u"a.ko{vcl}.{pah}si{acu}t".format(**key),
        u"akohsi{acu}t".format(**key),
        u"waakohs-i-t",
        u"boil-TI-IMP",
        u"Boil it!",
        u"sent"
    ),
    (
        u'a{acu}{lng}.wa.ja.ki{lng}'.format(**key),
        u'a{acu}a{acu}wayakii'.format(**key),
        u'waawaya{acu}ki-yii-wa',
        u'beat-DIR-3SG',
        u'She hit him.',
        u'sent'
    ),
    (
        u"a.wa.ja{acu}.k{sci}s".format(**key),
        u"awaya{acu}kis".format(**key),
        u"waawaya{acu}ki-s".format(**key),
        u"beat-IMP",
        u"Hit someone!",
        u"sent"
    ),
    (
        u'a.t{sus}{sci}.ni{acu}.ks{sci}n'.format(**key),
        u'atsini{acu}ksin'.format(**key),
        u'itsiniki-hsin',
        u'recount-NOM',
        u'story',
        u'N'
    ),
    (
        u"i{lng}.ka{acu}{lng}".format(**key),
        u"iika{acu}a{acu}".format(**key),
        u"okaa-wa",
        u"rope-3SG",
        u"He roped something.",
        u"sent"
    ),
    (
        u'o.ka{acu}{lng}n'.format(**key),
        u'oka{acu}a{acu}n'.format(**key),
        u'okaa-n',
        u'rope-NOM',
        u'rope',
        u'N'
    ),
    (
        u"s{sci}.ks.ta{acu}.k{sci}t".format(**key),
        u"siksta{acu}kit".format(**key),
        u"sikstaki-t",
        u"bite-IMP",
        u"Bite something!",
        u"sent"
    ),
    (
        u"s{sci}.ks.ta{acu}.ks{sci}n".format(**key),
        u"siksta{acu}ksin".format(**key),
        u"sikstaki-hsin",
        u"bite-NOM",
        u"biting",
        u"N"
    ),
    (
        u'a{lng}.k{sci}.{pah}ta{acu}{lng}t'.format(**key),
        u'aakihta{acu}a{acu}t'.format(**key),
        u'ya{acu}akihtaa-t'.format(**key),
        u'pack-IMP',
        u'Pack something!.',
        u'sent'
    ),
    (
        u'a{lng}.k{sci}.{pah}ta{acu}{lng}n'.format(**key),
        u'aakihta{acu}a{acu}n'.format(**key),
        u'ya{acu}akihtaa-n'.format(**key),
        u'pack-NOM',
        u'packing',
        u'N'
    ),
    (
        u"ii{vcl}.{pah}pi{acu}.ji".format(**key),
        u"iihpi{acu}yi".format(**key),
        u"ihpiyi-wa",
        u"dance-3SG",
        u"She danced.",
        u"sent"
    ),
    (
        u"i{gls}.po{acu}.ji".format(**key),
        u"i'po{acu}yi".format(**key),
        u"i'poyi-wa",
        u"speak-3SG",
        u"She spoke.",
        u"sent"
    ),
    (
        u"i{gls}.po{acu}.wa.t{sus}i".format(**key),
        u"i'po{acu}watsi".format(**key),
        u"i'powat-yii-wa",
        u"speak.to-DIR-3SG",
        u"She spoke to her.",
        u"sent"
    )

)

if __name__ == '__main__':
    with codecs.open('weber.txt', 'w', 'utf8') as f:
        for index, form in enumerate(forms):
            f.write(u'%-20s%-20s%-20s%-20s%-20s%-20s\n' % form)
