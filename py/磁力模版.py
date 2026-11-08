# -*- coding: utf-8 -*-
# 磁力列表源:把一堆磁力链接变成可点播的节目列表
# 数据来源优先级: ①ext 指定的 .txt 路径 ②本 py 同目录下所有 .txt 里的磁力(合并去重) ③内置列表
# 播放前提:宿主 FongMi 本身能解析磁力;本源只是把 magnet 链接原样交给播放器(parse=0)
import os

try:
    from base.spider import Spider as BaseSpider  # type: ignore
except Exception:
    class BaseSpider(object):
        pass


class Spider(BaseSpider):

    EMBEDDED = [
        "magnet:?xt=urn:btih:9362CB57E23942E1F37A5ECA46827FCCF192107B",
        "magnet:?xt=urn:btih:6D04C491362342153E565F6F98E0EF42B91EE2C6",
        "magnet:?xt=urn:btih:F8F7909164629DF76993CEF8C9327DE27D435FEF",
        "magnet:?xt=urn:btih:7E8B8011DA881124E0A041ED65DB5D0BD7957AB0",
        "magnet:?xt=urn:btih:FA20B7EE57F6BA36E5332D06AA8E70D2117D63CD",
        "magnet:?xt=urn:btih:CFF404E3ED887EFA35864E9E423DB2E01F5BAA27",
        "magnet:?xt=urn:btih:F4E6DAEF545F3D76E73F08D738B0514089CFC48E",
        "magnet:?xt=urn:btih:DD22369F228978BB8784851D941492FA8AD15BD3",
        "magnet:?xt=urn:btih:A7791BD8C0F249D447D49F0DCF7CDEA9C02EF3CE",
        "magnet:?xt=urn:btih:18C693D3325363E63E401DCB695350DAE2F05855",
        "magnet:?xt=urn:btih:B315D228F8C464026A871D1255D886C1CB04616D",
        "magnet:?xt=urn:btih:6407DC8F45916098C1266E13CAD88F86D65E7B5C",
        "magnet:?xt=urn:btih:8E80FD639222ABFB795153BE2A15DE05C2A0A0A7",
        "magnet:?xt=urn:btih:570F7C884E49644579159930D6E6CA86A1F6CAE7",
        "magnet:?xt=urn:btih:4506A520D615A1D6BA5BCAF80A91D194D250BB64",
        "magnet:?xt=urn:btih:A091A28ED62E9C125AB505587198BC4E029B02C3",
        "magnet:?xt=urn:btih:5603DC066C76F1DEEF461AA6B6DFAF75CF666012",
        "magnet:?xt=urn:btih:99CDED0182E6DD9EED4C8DE2792710D335A0B240",
        "magnet:?xt=urn:btih:AD3E226AD57D4D7C754156A0C5B3CE07799BAE6D",
        "magnet:?xt=urn:btih:073D0A8BFC8CD3198E7B845162DAA7F283B04B95",
        "magnet:?xt=urn:btih:50604AA10047ADC97D9981722D0DD9C20D64496F",
        "magnet:?xt=urn:btih:B2793FC382BDE02B4B967E1CBC96E21C2691C2D6",
        "magnet:?xt=urn:btih:31B84D6513FC70A03B111D29ACB6469941D991F4",
        "magnet:?xt=urn:btih:F132BD45DA3FEE40696D08ED0E6ECDD4F5686514",
        "magnet:?xt=urn:btih:B267D4CD21DECF879A25E79139D0F359208171F5",
        "magnet:?xt=urn:btih:62FDE755AEB9B5BB47F19A37336D179C2832BB42",
        "magnet:?xt=urn:btih:D72F88D77E0BBF3859B60A86518606E3F9D26143",
        "magnet:?xt=urn:btih:02F7A563536916B64F1507FCECA1FB6F10CFCD15",
        "magnet:?xt=urn:btih:8D964354A9C4E7CD7141A5F9CAD43310AB160C53",
        "magnet:?xt=urn:btih:54D746D0362128CFC886E5D83ED25309A1243235",
        "magnet:?xt=urn:btih:51F664DA7D37111F9B81537C8E30E6AEAE859F5D",
        "magnet:?xt=urn:btih:23494CC22E7A012C9BA4FA753BC1119D9A4C81AC",
        "magnet:?xt=urn:btih:080BFFF936AC58846F6511F4E3B58CCD8CE32F5D",
        "magnet:?xt=urn:btih:ED2F72D4D984108D7D6EC4AE878CAF28A8432B1B",
        "magnet:?xt=urn:btih:705314B4708BB9E1DEF3B9A10BA1FD39E5DF77D7",
        "magnet:?xt=urn:btih:4B7E2A60E6822F914227F9237B208B5C2E5C9521",
        "magnet:?xt=urn:btih:E949760EDC9FBCB046A7D00CA0740EDBB6151CCC",
        "magnet:?xt=urn:btih:0F246E36A03154FB509D7CC72835418843A5C34F",
        "magnet:?xt=urn:btih:B32AE54A1D539969A72744F212C8DA5A17B22C60",
        "magnet:?xt=urn:btih:14AC25C1B0D31CC9D1A49A253FB1DEE33723A459",
        "magnet:?xt=urn:btih:3BB5597DEACB9D888A9E3BC13966ADF7404EE5AF",
        "magnet:?xt=urn:btih:3C2E34C98850DDF9F8E36A40BDB9DD29E206876A",
        "magnet:?xt=urn:btih:1F1E4D72E139782BF65C059A2D7910FE1D046886",
        "magnet:?xt=urn:btih:DCDFD77862F41EB9B4250B587EDF384C08A4A5DB",
        "magnet:?xt=urn:btih:0B23D4DCF4F8F9E9B2358DF05F6F38CC7A3DAC00",
        "magnet:?xt=urn:btih:B6F4DCD6A3D02E4BCD4B671E8FB03B6B35658019",
        "magnet:?xt=urn:btih:D7F669349E6DB93E987BA8DF14C79ED066445780",
        "magnet:?xt=urn:btih:C53D4216CD05D593BB01CB322BF483A51809FFD8",
        "magnet:?xt=urn:btih:0D7185D71631850820CACA2863DBF7CCD3CE5A0C",
        "magnet:?xt=urn:btih:C963305928C8878AA266795AD9142EE9079EFDEA",
        "magnet:?xt=urn:btih:79849BCEE24B2B1E0B7771780E9967A71BDAE08A",
        "magnet:?xt=urn:btih:6986A344BC32B66CD1443DFC759EB14F03699987",
        "magnet:?xt=urn:btih:876480D952504035B4AFE06BE13AB56197285FC3",
        "magnet:?xt=urn:btih:B8D54458A7AA795294712325AA57122B9CB3461B",
        "magnet:?xt=urn:btih:B4B5150CD99899088599CA5DB8A122DED93B5340",
        "magnet:?xt=urn:btih:5027D1CBAD96302E8C2491D7FA00033F093B7B4A",
        "magnet:?xt=urn:btih:CACD5214F5D71CF61F4677DC5AD24F0A9B873868",
        "magnet:?xt=urn:btih:6CAE5C05891FC97578CD46608D9A9CF70915F349",
        "magnet:?xt=urn:btih:E149C762F9551C940BB6881F0C71A11D0E7FDC6B",
        "magnet:?xt=urn:btih:1F70DAA028245B8256B849855C40A18505CB1B13",
        "magnet:?xt=urn:btih:CC193FF3CE58038715AD0D62E8DF4FF9B894B3F5",
        "magnet:?xt=urn:btih:B86727BCFAB27AB8955DBA51094D5DF4A93980ED",
        "magnet:?xt=urn:btih:71585B59C2948864B1645A0924D0D4B79EE85D42",
        "magnet:?xt=urn:btih:BBE398B0F6BFAEABD746A70FED9D2F212EB61839",
        "magnet:?xt=urn:btih:55BA0700351BAF5BDC5199144E3259A1CB7BFF20",
        "magnet:?xt=urn:btih:3B8ABF5BF94E44778FFC3F4C4690E9746BCAB3D1",
        "magnet:?xt=urn:btih:13183979BADCC5E089FE22C0E72FC57A1EF09AE7",
        "magnet:?xt=urn:btih:3A05001D05D7B6C552D1D1D8393834D249042426",
        "magnet:?xt=urn:btih:CE2440F8F59288052A521043947A6167E412D174",
        "magnet:?xt=urn:btih:B22D33584A32AE7D472171A0EC72F8F9F3F9911F",
        "magnet:?xt=urn:btih:4A89166D949EB65B2166EC5BD1FC907663E9CC8B",
        "magnet:?xt=urn:btih:20CD25486A7E36B80D7F6273D6027630E05C5B7F",
        "magnet:?xt=urn:btih:93497CC6E7FD07BAC2FCFA13772DD37A340C39E7",
        "magnet:?xt=urn:btih:5CFAB0EC5E4D07E976A7C1739DCA19554AB64F2D",
        "magnet:?xt=urn:btih:59AF3DC321902660870F576E7AC9A8B7F353EDC4",
        "magnet:?xt=urn:btih:9F6AE7F04DE565995403C69802477B2570C53349",
        "magnet:?xt=urn:btih:BAA35F79B5B5DEFCD3845A5ADA1F175202A45F0D",
        "magnet:?xt=urn:btih:6349A9F5E53FBF9BB50EC68C6578613134B392B1",
        "magnet:?xt=urn:btih:15E2F7336C2DB5C5BEF31D3098BE255E1406BC6F",
        "magnet:?xt=urn:btih:4C9C085CFE3813CC6F7EE2F7375F193CABADE013",
        "magnet:?xt=urn:btih:6D4E4F208FBF0E6F2A83CB300B883524F4F8F12F",
        "magnet:?xt=urn:btih:B54AC1FC97FB05FEEB9E900EA39CA6FF3F25D792",
        "magnet:?xt=urn:btih:F7BE54473C411EEEB6FAFE52DB0F3CDA9F9DF177",
        "magnet:?xt=urn:btih:236DAF2C49E9A82CE57737FB43F7C76EF7AA89BA",
        "magnet:?xt=urn:btih:41FFB0060C521D41A6C594588958C707318AF720",
        "magnet:?xt=urn:btih:14728C514DF25DA32FA406F776819A7C5FDCAC07",
        "magnet:?xt=urn:btih:A307788C2508C5F0E08389E36D22D5F3161AF050",
        "magnet:?xt=urn:btih:1CE58736020A9BF24E078CDB17C52629D78AF61C",
        "magnet:?xt=urn:btih:E9FDD29A279BA183698D93171A779E419B19C367",
        "magnet:?xt=urn:btih:7619BB44148174B89289A0C693E94A2D15F536AC",
        "magnet:?xt=urn:btih:257E17CD9F442170609C5B0800C5A321EBEA74C5",
        "magnet:?xt=urn:btih:CD2EED6A5C827A64EBDF13136479A9AE157B35CC",
        "magnet:?xt=urn:btih:51A4C1628A435F8722987B0FAB71B3B25901DC82",
        "magnet:?xt=urn:btih:1BBB8EDC4CB6B08B00E22F314ABBE08525FB1121",
        "magnet:?xt=urn:btih:CA9C444BBBCA7893215A140F9B72D6842C380E2D",
        "magnet:?xt=urn:btih:B6578C387D2954FF2FC7170DBF2386C8B065C401",
        "magnet:?xt=urn:btih:6DB6AC4B41E3C773A16EACB0666ED00FA4F08CF4",
        "magnet:?xt=urn:btih:4F7232294C4D4639D8039F84C0A5BC8AEF0D79D4",
        "magnet:?xt=urn:btih:5699B4CD38BD39FA09CEBF160F3C38D2B2A522E1",
        "magnet:?xt=urn:btih:4673EBC6595A1E5D80734E1D3066D7D82E5A34F3",
        "magnet:?xt=urn:btih:4C49B89C427C105F808ACBC2C7CBA6453BD7DF84",
        "magnet:?xt=urn:btih:1890D1C7A59AC6F484699B078999569EE0782634",
        "magnet:?xt=urn:btih:4B9EDB94E0CAC8AE32CB35803DE380571F0A108E",
        "magnet:?xt=urn:btih:753C2A713722A3BA081959E985522E8578AA72FA",
        "magnet:?xt=urn:btih:6EA21AF521DBC5B418B86FF841BB08CB6E1693FF",
        "magnet:?xt=urn:btih:EE1403AF275BDB9C7F60F085F339FA371633A485",
        "magnet:?xt=urn:btih:AFF851F400A51ED182F33B7910D723EE4A885722",
        "magnet:?xt=urn:btih:5AC8B45FC6A62C27A2A5585C142BDD464A5F98FD",
        "magnet:?xt=urn:btih:23EB18ED3F57FFF2CE601AE30A0F0F1C1072309C",
        "magnet:?xt=urn:btih:7E41E241A3F3B7DB0EE188002B6EFF964C96A0F9",
        "magnet:?xt=urn:btih:10A5FF3D92B54DF3CE147AE87D509860034A21F6",
        "magnet:?xt=urn:btih:C9613822B40085F8B91625CB335DB88B2FADDA13",
        "magnet:?xt=urn:btih:1B76FBB8712F018372139BBB2F3933A785988719",
        "magnet:?xt=urn:btih:985DC856D4D56E625C05DCB2E6D8A8881913BD4E",
        "magnet:?xt=urn:btih:624F0BF224E6873A7D2E8E38E967D1248FE2F701",
        "magnet:?xt=urn:btih:F51F8B05C0954B87B9303203259B91536AFE05D0",
        "magnet:?xt=urn:btih:7D81440599BF98A83848BC2DA140BBD7283378E7",
        "magnet:?xt=urn:btih:69374D3E5B82BF004711B0B97F7ADB3F37820038",
        "magnet:?xt=urn:btih:7345226AB052008063DE49AF8F05E46641AC7AAB",
        "magnet:?xt=urn:btih:C3747AFD7A079941057E981DE615EB0123F62C05",
        "magnet:?xt=urn:btih:16BD9403B61C8E0DEB2199BBD7474412E022794D",
        "magnet:?xt=urn:btih:7D4ACF2FD84F4CC061061376CEC8A5281F000804",
        "magnet:?xt=urn:btih:8703FF47E26C569FAD6C63FDE87D78C256A498D2",
        "magnet:?xt=urn:btih:FA64821DC2B05CED45973250A42B50415EE7512A",
        "magnet:?xt=urn:btih:1744038C2542E30D66454DCDB151AF1578337DFD",
        "magnet:?xt=urn:btih:21673027FEA69771455E3F7E9B4255A0CAAA35E9",
        "magnet:?xt=urn:btih:F46DF03C85DD57D0D4E90904EBAC043ECD4382B9",
        "magnet:?xt=urn:btih:A6B69526CE1DFA0CD091ECD23C776678AB6872C1",
        "magnet:?xt=urn:btih:9F349CFFAFF4B7B38E185B6BEC870C497EC0FD6A",
        "magnet:?xt=urn:btih:56AABE2E43D7A7FC6B0490C162D1E810BAFEF263",
        "magnet:?xt=urn:btih:1996013EEC2E6BCECB35B5444CE2E60AB16A2627",
        "magnet:?xt=urn:btih:0BA72F6E88C22B2F5C055E7AE2A8D524F0E1DA91",
        "magnet:?xt=urn:btih:66C8EEA5FEEDD926C951C74B46776BCB559ADEC2",
        "magnet:?xt=urn:btih:B26E7A60C8EF532435FAD1DF13249240FA9BAED4",
        "magnet:?xt=urn:btih:B3BAD90B2A3D05026A2B969091A68F1352C737A0",
        "magnet:?xt=urn:btih:2E329A17374F328383A8B8EE1C24C9F6667A7E1D",
        "magnet:?xt=urn:btih:B1B019686FBA721E307EBB581C5ABCF1BD8D69EC",
        "magnet:?xt=urn:btih:4C243B64D7E0353F9C5E449E17F9402A3D2D1E87",
        "magnet:?xt=urn:btih:4B3040757CDE76535492B9D3DC828D35AE41D0EB",
        "magnet:?xt=urn:btih:C0D6B395BA2B7AEF95102A97D5B7283C242B6773",
        "magnet:?xt=urn:btih:34C5F1CA267CB584CCEB361951E857B9CA976F0A",
        "magnet:?xt=urn:btih:BD046EB783EC4131C32558A6CBEEE4D68453D267",
        "magnet:?xt=urn:btih:912F91B2F70C98502351ADD27E40DA09FD89AB10",
        "magnet:?xt=urn:btih:E7A108912478C68FB1D0911D475E79F67BC306E2",
        "magnet:?xt=urn:btih:4D6276003806D8BA8AD17AB5ADDDF28129E5B25D",
        "magnet:?xt=urn:btih:592E854CB04C19E951C5FC9981B85A94D3AA17E5",
        "magnet:?xt=urn:btih:0E3B974ACB70BE8703303C1BC28E848A418AA0B7",
        "magnet:?xt=urn:btih:D8C36C7A1ED48FB2C84DD3C3E1324D2BA2A463C0",
        "magnet:?xt=urn:btih:578B1676E2A40EA7A7F8B19BF9A62970E58E2CEE",
        "magnet:?xt=urn:btih:95713BE1B2921FE3DA0AE4DC5313B00C74B4C0CC",
        "magnet:?xt=urn:btih:98CE1FAEE435AD48EA419E172F81ED316D1898F5",
        "magnet:?xt=urn:btih:90B6CAF8440AE4160CB5756318D53AA1EB7C0B17",
        "magnet:?xt=urn:btih:02AC56F4DF0185D64E5E17FD0DC58C196F85B9AB",
        "magnet:?xt=urn:btih:02114916A9A51F4E2C04D5B2D4BF032C1AA4A830",
        "magnet:?xt=urn:btih:7896E29C5F2636E617CD16695E425606440E627D",
        "magnet:?xt=urn:btih:F5B3C64A25021D7AF2644A10531AEFA1E4D84DA0",
        "magnet:?xt=urn:btih:74B3FA23E68654F2A97021A4F393962623A11CA5",
        "magnet:?xt=urn:btih:695C421447F038FA09C513C373D78CFBB555091A",
        "magnet:?xt=urn:btih:AFF822A75207781D3AA780B08703D00AE6CC5476",
        "magnet:?xt=urn:btih:B2F7BFA6ED3BAA6D8C29947BA1D9AEEC73A8C835",
        "magnet:?xt=urn:btih:B365D8911B4184CD217F1E38BC3118C526E13780",
        "magnet:?xt=urn:btih:A53AE5219E0EA188AD1438D9D0A1EBD567422D1B",
        "magnet:?xt=urn:btih:D33ABF4632538D527E017D0742349850ACA2DC22",
        "magnet:?xt=urn:btih:4E770E63EC01D09C82B91552694E93788FAF8807",
        "magnet:?xt=urn:btih:508D0FE40B287F0EF742D8DCCE0BD5CD985894D6",
        "magnet:?xt=urn:btih:8B539A7F328F2039DF5AD653C4C68D1D9C063246",
        "magnet:?xt=urn:btih:EAE8FD7E26EB107185A114BF2E97369BC0A3C2F6",
        "magnet:?xt=urn:btih:72903AA70711BAF3DE2EC26945C2DA22B940A4B5",
        "magnet:?xt=urn:btih:812888D6BF53517332FDA6D56D527CA7F2E9F350",
        "magnet:?xt=urn:btih:AE53AF0320743056312E09484130952216D9EF8A",
        "magnet:?xt=urn:btih:499B1274BCD9A67961AE14CA4F657FB46B18BB41",
        "magnet:?xt=urn:btih:2B56B50A9926085C4CBCC2D1563BA7B8E5B2C624",
        "magnet:?xt=urn:btih:4711807F74604473F69285199758573D78196804",
        "magnet:?xt=urn:btih:355D9FA19FA7BB850383C8DA914FE2BF07240E8D",
        "magnet:?xt=urn:btih:DF0256FE2B5506850D93410D71C9443C24E17D5C",
        "magnet:?xt=urn:btih:9A4993930C035063A9D1EBEAE4E8EC84AD4D1520",
        "magnet:?xt=urn:btih:489EC682106D9ABAF3E782FC89E913819D7C85FF",
        "magnet:?xt=urn:btih:E37F439DDC0C31DF25CF8962EC0FC5C70336608A",
        "magnet:?xt=urn:btih:7C2CF774C0944F8536A9E48166F3C56E3969E5CE",
        "magnet:?xt=urn:btih:6950EB0550A2713707A0E840CC068A20D5982543",
        "magnet:?xt=urn:btih:2F97BE51114972FBB327FB3A5A60E3B0D13B17F9",
        "magnet:?xt=urn:btih:44E60F42AA377CEB1F2C479C54873C22A40B3EA9",
        "magnet:?xt=urn:btih:B11C444C88CFFC64E7D848A242A16FA2787A32C5",
        "magnet:?xt=urn:btih:B1152A9F6909D69D58A9AE399F21BEC754DAA702",
        "magnet:?xt=urn:btih:BA55B128BC421EAE0C75226EFC1B60702E74E094",
        "magnet:?xt=urn:btih:D38FBCE7A7AE13C3B46F2544AC5F16FF4FE45642",
        "magnet:?xt=urn:btih:BA7B9B719357D44977ECA2B05C1E1CFD66D22D8F",
        "magnet:?xt=urn:btih:5A003D9D55833D67E815B676E10E3DA303949B69",
        "magnet:?xt=urn:btih:7BCEF02FD40329C8BCBEFE88BE66716988060D05",
        "magnet:?xt=urn:btih:EB03DD40722759E7119E0A22E9DF6BD1255F20C4",
        "magnet:?xt=urn:btih:FBC8825CA93F952124BE35F9C6B3E2FFCF435AEA",
        "magnet:?xt=urn:btih:E3A29EBBBEC06AF312DCE722E7E59AA1F5DC94E6",
        "magnet:?xt=urn:btih:5A73F82FEB85E8174D72A5EC2E38B1B46151340C",
        "magnet:?xt=urn:btih:DE6C6A6733C2319C3E9EEBD7A955D8DA4284FEBF",
        "magnet:?xt=urn:btih:5E2FDE4A60B1A0170331FC461323B9F17063DE06",
        "magnet:?xt=urn:btih:7BB625C1B8CE22563F41F36C24454FF39B6341CA",
        "magnet:?xt=urn:btih:6D451A671C4DE771ECF3A896339C76E01B5BBF51",
        "magnet:?xt=urn:btih:32C956A8AC65629C32551533981FB7CE3DE39C27",
        "magnet:?xt=urn:btih:ED578AD46187CEAC218082CF13C5A7F84AAA051C",
        "magnet:?xt=urn:btih:69487B60AF4CF7281C4C22DE13CD48A233CCA072",
        "magnet:?xt=urn:btih:7A57701EA9A3EDA28FEE5250CADF61CAD0422A13",
        "magnet:?xt=urn:btih:F254F7024353456FA90A9866BD415DEAE4939553",
        "magnet:?xt=urn:btih:BAC9252CD2973C257C2F9A6F01E36D2015BE30D0",
        "magnet:?xt=urn:btih:CEE1238F1D2A6FFFCA84529812ABE68048A07AE0",
        "magnet:?xt=urn:btih:2A00648C1812AAA73CC1E1BD1B7B14F91E6BC477",
        "magnet:?xt=urn:btih:E696C79D2D770E4AE9EF8651D71F0719A8407A2C",
        "magnet:?xt=urn:btih:718333D8EDA7199396B2648B389117BD453B1EA7",
        "magnet:?xt=urn:btih:999C7099498853D53C3E83428C4B4A72C04FBBBB",
        "magnet:?xt=urn:btih:D14A54B76CAF576E499AE6AD32907AC4608CDE8C",
        "magnet:?xt=urn:btih:FCF13B68214B2BD16303B5553B7826A25CE7F0AB",
        "magnet:?xt=urn:btih:87763FF581DA02BDBF8B7783953BCEAFADC3830F",
        "magnet:?xt=urn:btih:8B03C343020F1F201AA9AF5E3D1F34DFC6413544",
        "magnet:?xt=urn:btih:0E186BCCAADA57973C890C2C60CB2F30C9BD41E8",
        "magnet:?xt=urn:btih:3F33BE3E53167D72B70D3A11C900164D7D53A626",
        "magnet:?xt=urn:btih:E423F03C3E8B3B830D12D3F94B85741C6099A698",
        "magnet:?xt=urn:btih:87FFAF70E7DF9B504314077A6259C702FC69F4F6",
        "magnet:?xt=urn:btih:B39641EBE6A099DAD65B5EBC3666246C89D89A65",
        "magnet:?xt=urn:btih:5EB0BE8670E3031E2B2F281277FECE10B041F141",
        "magnet:?xt=urn:btih:9C0ADBF2161767A7C0206E45F575A147685C1D8F",
        "magnet:?xt=urn:btih:99A7784FB5F64F657D66FBE34399A791C27991B7",
        "magnet:?xt=urn:btih:3BF885137D2DD61148D659F7408018EBE153AC8A",
        "magnet:?xt=urn:btih:BC099913B57F729DE8D4D239B8FBFB085475962E",
        "magnet:?xt=urn:btih:53521BA91C1B1D554F5D990143C38508C45FB809",
        "magnet:?xt=urn:btih:D83A90E24FE9495B24AABCD3139B491C4BEE462D",
        "magnet:?xt=urn:btih:0E81D1595FF867805A130E505CD5C690624402F6",
        "magnet:?xt=urn:btih:89D9AF566998E161D0BCB03691A7E7BD90645D45",
        "magnet:?xt=urn:btih:1411F85F29AD76D0DAF389246E24D7BD1212497E",
        "magnet:?xt=urn:btih:536ED3FCAF48615F4AD1EBE4DAB73FBEE5DF2F49",
        "magnet:?xt=urn:btih:44A01555D3E61878C48B83C8E5574DBD19B85846",
        "magnet:?xt=urn:btih:7BB082DF860DA8E0998C28DFE5B5DFC7DB31152B",
        "magnet:?xt=urn:btih:CDF8817F8B4A637A2C32900235473512909F227A",
        "magnet:?xt=urn:btih:77875E92D497E20E432247EE331AC89B5417D66E",
        "magnet:?xt=urn:btih:2DC75112626BCFFB10CCBCFFFFF772452C5FA3C5",
        "magnet:?xt=urn:btih:C40EA13B402D6A155BC5B4B557971DD80272792D",
        "magnet:?xt=urn:btih:FB097FAE09F67F7542A51ADFE50F2DD420671B7C",
        "magnet:?xt=urn:btih:59DD03C23BADCAD30685D0E023F22AD1992D7F98",
        "magnet:?xt=urn:btih:573993CA0C11F261D9F7C5C9D552914B4DBE4DDB",
        "magnet:?xt=urn:btih:6B0EF3D71B54707950DEAA8C103F2357EE425A66",
        "magnet:?xt=urn:btih:6AA3CB409109889C1F0688CD191D4A2A8BC703EA",
        "magnet:?xt=urn:btih:683A553267F9EE423EB5C3CA9C1136E3ADF3A5FC",
        "magnet:?xt=urn:btih:E32B9C500E97F4A871D1D6F53FB510F529E8A4FB",
        "magnet:?xt=urn:btih:31DDC2ACA2C3B63DBA50BFF0D2A59D3E93CBA983",
        "magnet:?xt=urn:btih:4E55604920CCC9E4F0F4807E8FFA079A444533D7",
        "magnet:?xt=urn:btih:F86DD85DF8EF79EC0C8897CDBFCEC73893E7EC64",
        "magnet:?xt=urn:btih:960E036A7B5000E8C90BC87D328F24447F19AC73",
        "magnet:?xt=urn:btih:2063148E21077ED0F525C4A68D54594516A81349",
        "magnet:?xt=urn:btih:6958D446EEA25D8228B12184C99EF697CF2F5AC8",
        "magnet:?xt=urn:btih:DE7C9E588ABF1B6126355C9A5C3B2FD796B53BAE",
        "magnet:?xt=urn:btih:3A7FB023F21497D9478EDADA69FC2B007DBFE71E",
        "magnet:?xt=urn:btih:4AC0C5B2C17FB9C99A4131EBA88626C7371B4B58",
        "magnet:?xt=urn:btih:76C6222E488042D0FCFA9E49FF47B040884D6E83",
        "magnet:?xt=urn:btih:5E5C679F98C90497AF2F893107C5537BDE5D6D59",
        "magnet:?xt=urn:btih:045FED5EB043362BC2C9CC16622ACF2A5D246017",
        "magnet:?xt=urn:btih:DB4FBB971399531A6131BFA3EB33F1FCA0DE60FC",
        "magnet:?xt=urn:btih:7ED4FEA6BA68067F197547D808412BAC95A05945",
        "magnet:?xt=urn:btih:F8A0E0EAA19F09E0FD7753DD901890211A83681F",
        "magnet:?xt=urn:btih:66F8AC2D08C23075ABA4AC12E6A39D478BBA4526",
        "magnet:?xt=urn:btih:12A466A322FB054BBE133B51EB3F97AC8244006E",
        "magnet:?xt=urn:btih:8A479043BBCC9C1EF4B4D0EEF60B0533FF36DBB6",
        "magnet:?xt=urn:btih:6BDDD82B6798D702D63DF133BA58AA7FDE8978B7",
        "magnet:?xt=urn:btih:86770D650AF677A3511AB66D8C7E619D83F01971",
        "magnet:?xt=urn:btih:EFB723641200F9AFFC45E1156CFB17A6A3D66F23",
        "magnet:?xt=urn:btih:84860E98F90057FDC10ED8DCABC237C92E23B245",
        "magnet:?xt=urn:btih:EA260F31A596134EB9DDA771EDC4C90FF5BB7CC1",
        "magnet:?xt=urn:btih:78DD86CC7DCB109BC500DBA679724543FB6817CE",
        "magnet:?xt=urn:btih:405D45F96DB9D3D60CEA0B6871AC91145D67151F",
        "magnet:?xt=urn:btih:28A2A77FCD21DDCB7470B9CF8AA80A390140C11B",
        "magnet:?xt=urn:btih:927E931075AB4CCBB20DCA75D7ACF715F40E37B5",
        "magnet:?xt=urn:btih:652C7FCF440B4441FC1B03F92E527C9DEB25DC65",
        "magnet:?xt=urn:btih:4C81664416521828E13C31B9FCC657C2DDB8E3C1",
        "magnet:?xt=urn:btih:4F7DC1BF3F676321EEB756CB281B468273A10D61",
        "magnet:?xt=urn:btih:E14F912C7FF7D690B4BB69FA5C893BFE1F6A2ACF",
        "magnet:?xt=urn:btih:E2DA13B7900B2A4E6C40C3ECB79D022017456429",
        "magnet:?xt=urn:btih:C7A748A1BC0A574A4362CF44C1C2F82F0A2359BC",
        "magnet:?xt=urn:btih:0FFCADCE0B3C0CCC4F665A62244CF75DFB46E1BA",
        "magnet:?xt=urn:btih:55832A66254D115B404749609078CE30E75236C9",
        "magnet:?xt=urn:btih:A70693C30BD85B0A5F7AC2A4D3C5088BC22F21E5",
        "magnet:?xt=urn:btih:4093907D81A1608DDFEF94CF97BADD7473179B53",
        "magnet:?xt=urn:btih:52C8B34D34C8C7C3DAFD0B655FAB3D876E5AF1AE",
        "magnet:?xt=urn:btih:E960DBFD1F6D2516FA2A2D00E4C23A4BC4647846",
        "magnet:?xt=urn:btih:832BB8C3FF02D5CB99E4F262031643E4182608A1",
        "magnet:?xt=urn:btih:938723BDA978AFD62F66C6AE604B76142587709F",
        "magnet:?xt=urn:btih:A0AD6B5F367C6F4A67605717F70A429B8C0FACDC",
        "magnet:?xt=urn:btih:199AAF9402E7BD3E84ADC3804E4CA47B265486D9",
        "magnet:?xt=urn:btih:D96E8E73DFEA8AD674B4E84452A5535E500A2FF5",
        "magnet:?xt=urn:btih:02AD6DF060E6499712EA89CAB76B833EA1E2E38B",
        "magnet:?xt=urn:btih:7A4D00AE743C48908867594C2435AC0E272E6196",
        "magnet:?xt=urn:btih:4313A51FBBC68B5483992E386C6F3E3AC7760B9A",
        "magnet:?xt=urn:btih:C979D29FE021C9F9BF9095BEF7A16EEB49186F34",
        "magnet:?xt=urn:btih:B2309E684A59FDA4CA1D6C2C8552347457E24EE0",
        "magnet:?xt=urn:btih:8FEC32A97860AB4CA6B87458D2E5C755D06EF0F6",
        "magnet:?xt=urn:btih:07A6E974BDFCEB0D93C429D8DF977C1A8AA7324D",
        "magnet:?xt=urn:btih:44EDC1F6574F7CDEC0745D9813210A2BA02F3840",
        "magnet:?xt=urn:btih:C9BC80FC7234AE286B2E9AA0E38546B98EAB59AB",
        "magnet:?xt=urn:btih:980B45CCE66A9274EBE99497988497D223900C5E",
        "magnet:?xt=urn:btih:9A98802BF5DA59C246088AEEFC53D69407C7A3B0",
        "magnet:?xt=urn:btih:C5CC1803E1476E2938E96A9BD7F0C293D980A59D",
        "magnet:?xt=urn:btih:71F98FA3FF4A7B5A231A80E819B55CAA4540DD7F",
        "magnet:?xt=urn:btih:706975F8B51AC34DBB6AD0686EDBC8FD2465995F",
        "magnet:?xt=urn:btih:05352FC00E58BCE29DFC5F898BA23C4540A9E81D",
        "magnet:?xt=urn:btih:998F99D1D11CA80751894F77DDE92291093B6702",
        "magnet:?xt=urn:btih:DEA498B78D30F7101DFA447AF13FAD63939324EF",
        "magnet:?xt=urn:btih:5C9CA9351A26AD6C6B08817E7FCE43E3523C18DF",
        "magnet:?xt=urn:btih:5E0AB6AD81268A8FADA8C5594F4FBC237661E38F",
        "magnet:?xt=urn:btih:38E2A0191B406AE8E4D697973DE0818108D3BCA1",
        "magnet:?xt=urn:btih:8A22AC6A4CB204B0FB6AFA75C0095564F86B1CF8",
        "magnet:?xt=urn:btih:6D95CA215F181222CE7CC17C9C8A7E66666A8EFA",
        "magnet:?xt=urn:btih:66994F6FA02E4FC00D42305A372B34171595AF43",
        "magnet:?xt=urn:btih:3180719C74BEB1DD633942E9C4B90A36D9A239D0",
        "magnet:?xt=urn:btih:62D2187DA11ED32F0AC6ACDBF240BCDEA9DD34FF",
        "magnet:?xt=urn:btih:DD1D2C8F0D0C72BF7ADFF782321BDEA368B741F2",
        "magnet:?xt=urn:btih:8A88FC58C52FB91F4877CD653356645CF341FDDE",
        "magnet:?xt=urn:btih:E51334F717C6E245F397BD7CBF310777CF5ABC29",
        "magnet:?xt=urn:btih:93245EEA87D240920FDFA944C0C4B35F67381DF5",
        "magnet:?xt=urn:btih:4B1CF1BC77E512E9B562EAF77E71B23A14688B6C",
        "magnet:?xt=urn:btih:2B97D3E094DBEBF6931971277D1A6329D60B6E97",
        "magnet:?xt=urn:btih:220164D815E8770754FEF782E9600F24101BA189",
        "magnet:?xt=urn:btih:22E2B3B9EDBBF9C6BC3BBE24712E4275FF63C1C2",
        "magnet:?xt=urn:btih:911F14941A7D6556C82B80446DB897338D659D08",
        "magnet:?xt=urn:btih:38F9CDCA78DFFD0F1FC4EA44C169B8B91FD3E29A",
        "magnet:?xt=urn:btih:6E590AB5612E52643E5DEF7EAAABB5E4E74E014F",
        "magnet:?xt=urn:btih:32FE2B709E3A8F5813DEE1DBF8DA611DC4B4E4B9",
        "magnet:?xt=urn:btih:2BF455E39124CD71810FB27EABF3E3C83ECC6649",
        "magnet:?xt=urn:btih:EC648422795F64D663AF2A29BBACE5A0111E988A",
        "magnet:?xt=urn:btih:5DE6D2F5BDA2D2EAAFE7B17AC246EF756E59AFD6",
        "magnet:?xt=urn:btih:87F2BEAE6667DD46E5D7BD5A8757C62DC129BDC1",
        "magnet:?xt=urn:btih:05D3908824490ADF81BD1601D30B2A18AA10680A",
        "magnet:?xt=urn:btih:13B965A7E77E11867F3B19BF3964D614403CD625",
        "magnet:?xt=urn:btih:E955AA4DCD90A574252C8217659DAFD2492DFEF3",
        "magnet:?xt=urn:btih:DC6E4F576514B962057280FD65B6B2ED0EE22746",
        "magnet:?xt=urn:btih:D76E4243528B1E609D2C67C48722B7E61A04F5A9",
        "magnet:?xt=urn:btih:F2CB402B3C23F491C9B0FFFED686B71B126E751F",
        "magnet:?xt=urn:btih:333DC346A786265F881BA4EDD3B070506261359B",
        "magnet:?xt=urn:btih:4BB06B6273FACB92A9D4E948DB09B627A736D117",
        "magnet:?xt=urn:btih:804751D5FFB0D5DEE3A6789D5794309A02EE1B39",
        "magnet:?xt=urn:btih:B8E71DA9ED8582777B6289623B417560EEBD12B2",
        "magnet:?xt=urn:btih:7905FDB07CADA38AA5FAB96D7436662FC7BE2739",
        "magnet:?xt=urn:btih:BFC10A608B474E6EA23EA175564EB91AFBBBAAF9",
        "magnet:?xt=urn:btih:0BD81573BD15057DF39B09B483B51BBBDD6D5231",
        "magnet:?xt=urn:btih:804E5C9B013EAEF0D87F9119F2BD93C5120ABD60",
        "magnet:?xt=urn:btih:5B64B059C5E96431DACC530A8049802A2E859605",
        "magnet:?xt=urn:btih:8E7C309CD646BF45E94970870896AAAA73434511",
        "magnet:?xt=urn:btih:3B36C49B9667950F485EC731BD70457952D1D0DE",
        "magnet:?xt=urn:btih:C1444499525B1B2073C145C64001B2D485E5D3F6",
        "magnet:?xt=urn:btih:7643DB1F604F5CED770E330242B2D72DECAC5FEA",
        "magnet:?xt=urn:btih:FF55BFF11EEB255C17B592506CF1E951BD0681DB",
        "magnet:?xt=urn:btih:F6D8B39C32D9A78796B6632A2FA989128D087376",
        "magnet:?xt=urn:btih:B26DD11933310FC82246F46B465474250F33C764",
        "magnet:?xt=urn:btih:ECBAD288AEC58330C8DE9514FEA63C117D6CCBEC",
        "magnet:?xt=urn:btih:3584FB9DBDA17A71ED3FE87D04EF75F7A56722C4",
        "magnet:?xt=urn:btih:BF5D1AB42A2446CFCFEC6382C9B0BD4BFA082FDA",
        "magnet:?xt=urn:btih:7B92F6F0FE9D75308117E7730E2B4ED4CCD3C50D",
        "magnet:?xt=urn:btih:1F808316ED8BA8A0FE414C38701296C9A5705AC5",
        "magnet:?xt=urn:btih:63655D5C1DC77C6B8794EFC9AD9C5015B4388132",
        "magnet:?xt=urn:btih:1DC54BC9F73B96B23238ABF3D62662666ADAFBF1",
        "magnet:?xt=urn:btih:EE5427D8113D782775430E0E49EA9E06485FC91B",
        "magnet:?xt=urn:btih:D068B1B30FD293DE4453694C8CB76B083CD48349",
        "magnet:?xt=urn:btih:BC58F73895D9452F93C430E6C619B18435FDDC10",
        "magnet:?xt=urn:btih:301E5882AF9E5AA177E621EC43320096812B8E88",
        "magnet:?xt=urn:btih:262533E064F8026EFB827384048E9D0BECF92B3C",
        "magnet:?xt=urn:btih:6E8D9828141B518A5A32913425F22CB8D532C8C8",
        "magnet:?xt=urn:btih:8624214070C7FD16B73DC7EF3FB4CB82A1B35501",
        "magnet:?xt=urn:btih:C7B20DA0DA8B97A898B4BB3D32927BDD5F81CF0C",
        "magnet:?xt=urn:btih:DB0DBE4600ECE43D4EFA5FE92F4C3E254B127405",
        "magnet:?xt=urn:btih:237ED889DB216D2FBB082A838B3CC9CADCE98134",
        "magnet:?xt=urn:btih:EA57FE390B1A9DFC4499DA87A136297CEBE572E0",
        "magnet:?xt=urn:btih:4FAA5956DF7ED47D8788E0FB7E5F15884A1DC666",
        "magnet:?xt=urn:btih:0EFC1D4041BFB740B9A850DD01C2812F135A0E40",
        "magnet:?xt=urn:btih:127758F7A6510DCCA0A8A9668D3A521D461BED77",
        "magnet:?xt=urn:btih:6793AD12E63FBA0212FE64898D8627A6712E4EE4",
        "magnet:?xt=urn:btih:2DA92A8590F449CA8896FCB05090CFCE805E2338",
        "magnet:?xt=urn:btih:A3E4A513C9B5D634D081EAD91CD62DCD3963C5EF",
        "magnet:?xt=urn:btih:61CEA4521C220EC182B547819E92C1E8E6B33350",
        "magnet:?xt=urn:btih:DC134E071218FDF314B8019B4635376BD25B4DE8",
        "magnet:?xt=urn:btih:29B75470D6FF99077093EF5D410C8C2132FBB19B",
        "magnet:?xt=urn:btih:2D622BEEFF9E689BD9161DB7A8EA971CB9BA80BB",
        "magnet:?xt=urn:btih:67BC6AA41ED75802F81EA4F5A32BD9098E53A9BC",
        "magnet:?xt=urn:btih:942A4DBA3047C99FEF3DD354A1668DD9B3D58E71",
        "magnet:?xt=urn:btih:0ECC947C273750DBADD2B6CFFBF1CB2E4E6B1A18",
        "magnet:?xt=urn:btih:81AC0D872EA400F2FFA23863D77ED43A4B88EEA5",
        "magnet:?xt=urn:btih:063D48431EA4BB49D8505FD8928310FA338E74A9",
        "magnet:?xt=urn:btih:6B8F4E51E658897844526F14B8AA7D7E72C0B9CB",
        "magnet:?xt=urn:btih:A0EF07CCF84426FAF2E27D3A09E6C15BCD21AD9A",
        "magnet:?xt=urn:btih:25C63875FE2617C04C8A480F05205149135C9132",
        "magnet:?xt=urn:btih:44AFEAF59F785A81F63B98BC23B8CAB2CB632B75",
        "magnet:?xt=urn:btih:086CF95426BADCCC88F2FC53319EE7434D353E9A",
        "magnet:?xt=urn:btih:742006FEB4E25CFB02F19C72DE9FE151F3FC71E7",
        "magnet:?xt=urn:btih:791A29242CEAB008B8DD99AEB158474B4CC0085B",
        "magnet:?xt=urn:btih:673812F2C0B5E3578D6AEC9942757620998F61B6",
        "magnet:?xt=urn:btih:F31731D1052343CBED301B9560FB796894A2B505",
        "magnet:?xt=urn:btih:ED1C42D2A8B87CC410B7D8B9E81799C27906452F",
        "magnet:?xt=urn:btih:E2A9E58045E757BCCFC958F0A76BEDCF19C88363",
        "magnet:?xt=urn:btih:7BF98C57E7C8A792D9841316588892B28C3CE2AB",
        "magnet:?xt=urn:btih:9055CF044D2FE3400E35600082ABA109458D07C2",
        "magnet:?xt=urn:btih:CF1ED00374BAB76311DFE9E551439B2400E1BE71",
        "magnet:?xt=urn:btih:DEC2067EC2696BC0E0D994800476D22B7DC9DB21",
        "magnet:?xt=urn:btih:33B2A316244806714F4D7F4225558663C652BCE8",
        "magnet:?xt=urn:btih:3C4F4793EEA310E38DFCEB1E8160D81ACAFBEFCF",
        "magnet:?xt=urn:btih:0B93D7DA2DFC38E191D30AAC7F79C907D35827CD",
        "magnet:?xt=urn:btih:F790492F66C402B717A0A43F03164694CA878FF0",
        "magnet:?xt=urn:btih:932C3E2F6141D9E4B94BC2ECA3B6CD817149B4A5",
        "magnet:?xt=urn:btih:E41BF7990D85D8EF4302B8C89AC9BAA34391ADC1",
        "magnet:?xt=urn:btih:FF66C3EEA1313C488D15573E39502905915DB31F",
        "magnet:?xt=urn:btih:D76513B4D61AEDDD1DE4037D8F15866E233A6FCB",
        "magnet:?xt=urn:btih:1940728CF6118472600DD5A02D1EFC5AF256C09F",
        "magnet:?xt=urn:btih:AA65D9744F281EDECA4608C37AB833A066271656",
        "magnet:?xt=urn:btih:3CDD9EA5D353B1C9A6514AE04188ED3086B1E0A5",
        "magnet:?xt=urn:btih:3EAD8D4CBBE9D0C5EEE1CAE8AA398BDA4D7AD244",
        "magnet:?xt=urn:btih:44947BA7EFAFE874169D836042C3AF128DD35660",
        "magnet:?xt=urn:btih:96F222757A8C66584A19150AF71D3934168ADDE3",
        "magnet:?xt=urn:btih:F5A064805CF847566A46F765757BF3A3189A5E2B",
        "magnet:?xt=urn:btih:C4A0F892B366B11A24AAA128A224F9FC2A6D566A",
        "magnet:?xt=urn:btih:F221533D3D958E5B74673D481499200E963FF793",
        "magnet:?xt=urn:btih:1D70E334DC94ED1D1369639287211E95384A3FD9",
        "magnet:?xt=urn:btih:21987D62154762F6683DDC64F535D0DB696B3131",
        "magnet:?xt=urn:btih:7BDD775A9FD58CD02E5B2D67EEA917775B6A5801",
        "magnet:?xt=urn:btih:DD9D7309B31626434F27C95B283B59905EEB6911",
        "magnet:?xt=urn:btih:EBCE1E8BE1C68EFA98BDB6AE89645600DD26A803",
        "magnet:?xt=urn:btih:9F5ACD91EF0E3B56F71A0834463A68682B4AD431",
        "magnet:?xt=urn:btih:B0DD8731978610FBDE2BECB7B8132E91A7CE33DB",
        "magnet:?xt=urn:btih:B5351576D1606A1BDBF6E60A25EA443A5D960AF1",
        "magnet:?xt=urn:btih:8DBF76D4A361E105EC2BA5C9368EB4CAB2DBFD95",
        "magnet:?xt=urn:btih:826DB27BD466EAF20BA5D9D9E78C71C278C20079",
        "magnet:?xt=urn:btih:28E708949810B9C451A0D438DD9752F8757E55B6",
        "magnet:?xt=urn:btih:89DC469A7F7896F9C5DEB62789ABBCF7D10AEBBF",
        "magnet:?xt=urn:btih:11A726FB19D8CBAF5C97CEEF25A3F0608CD5000C",
        "magnet:?xt=urn:btih:345337F5589A47BC7BED060B329CAA521422BEBF",
        "magnet:?xt=urn:btih:7773F149742531BED50507014AF779013D246DCF",
        "magnet:?xt=urn:btih:A6C0BD0725F39E1D1DB989196E1B8337F4D892E8",
        "magnet:?xt=urn:btih:B3CB9329BE99D34ABFD06886B6776C8B213F5A6E",
        "magnet:?xt=urn:btih:6D6F5EC1E7B976D9401742513B1BF44D6C4D3B76",
        "magnet:?xt=urn:btih:7457A4ED150F0F843A64914B22794650EB3BDE13",
        "magnet:?xt=urn:btih:8E6B2E0B43EF6E1CE46B50AF709761F41429AC52",
        "magnet:?xt=urn:btih:F1D5A32AD3DE35DC9DAD61A37FBE9C55EB7E4A27",
        "magnet:?xt=urn:btih:43469AA835D5477D659BA8C427B6BC443346C549",
        "magnet:?xt=urn:btih:6A67F8AA7D5A8C8E63541A4B2EDC078D5B8262FC",
        "magnet:?xt=urn:btih:2A7CDD831327564FA8B908B83CC8E99922C19D11",
        "magnet:?xt=urn:btih:6D31DAC042C44B6A53D600E80A00C1BD50DE8E44",
        "magnet:?xt=urn:btih:2525757EBB05F608CCAF7820E7D5AEF9751FA3E1",
        "magnet:?xt=urn:btih:10F67FE45B18B802B4F7CF449A773A12E3FC30FC",
        "magnet:?xt=urn:btih:35630629FF6A29395E11626696D58BAB1B95E081",
        "magnet:?xt=urn:btih:CB86505E419374636365C0C6883885CE715597A6",
        "magnet:?xt=urn:btih:4B2D291D2EE8A454C6A716754DF0C7EDA6878B90",
        "magnet:?xt=urn:btih:EA6D3396F2939F0052E0E094FA5891FBE83EFEF7",
        "magnet:?xt=urn:btih:81DA48825EF40F4F512B2A6F9C6B0B34A0B0DA22",
        "magnet:?xt=urn:btih:788E27C2EAC39C4B7F7C3EEF008ED2EAF24AF611",
        "magnet:?xt=urn:btih:B79455090084CA85D76ECB3D9858560B417AA0CE",
        "magnet:?xt=urn:btih:8D085D30E780D22441416CBEDC72A8EA80969D73",
        "magnet:?xt=urn:btih:F135E9AD57231BF206898E639A4A33E15A17D250",
        "magnet:?xt=urn:btih:7C4969681AEDC305DB7B95C121BBA0019CC3C923",
        "magnet:?xt=urn:btih:6F543CEE1D1224B8D55678B5428287CBEB278AF8",
        "magnet:?xt=urn:btih:4792A6CDDBA9BE642CC8CDB8612160A43B5AD845",
        "magnet:?xt=urn:btih:64D6AFD43A843BE41BD48213344B2FD71F32D150",
        "magnet:?xt=urn:btih:2B0E6632209A166BA0B6893E14C4467EFAEF7328",
        "magnet:?xt=urn:btih:5C8EB81EABD5A49F3028A4F94F83B0326D187540",
        "magnet:?xt=urn:btih:84EE6ABFF74265A288E70B9EE5B958086FCB559D",
        "magnet:?xt=urn:btih:D2B48C8F2BC56F4775C827B96CCB88982AC5C597",
        "magnet:?xt=urn:btih:A571CE926C5754693EC9B13AD332ED1CDA7AB366",
        "magnet:?xt=urn:btih:B251FC10402EEBCB07033FC2E51B09A052375910",
        "magnet:?xt=urn:btih:37FF39DA572C83FC1EC8491115235C32AA976F22",
        "magnet:?xt=urn:btih:3C6E6F91ED1B3AC3465771BED7B13A215550DD1D",
        "magnet:?xt=urn:btih:5B314623582385C31460D3C29FD65979BAB13C73",
        "magnet:?xt=urn:btih:67E98AD6385B8DAC6BB64C3634F426E1C8B94D98",
        "magnet:?xt=urn:btih:88694F6D29882DF07A4600779E27E33A9ED4298D",
        "magnet:?xt=urn:btih:3617A832683252FD9D06F0FB57A9783AC8ED907D",
    ]

    def __init__(self):
        try:
            BaseSpider.__init__(self)
        except Exception:
            pass
        self.items = []

    def getName(self):
        return '磁力列表'

    # ---------- 数据装载 ----------
    def _from_txt(self, path):
        out = []
        try:
            with open(path, 'rb') as f:
                data = f.read()
            for line in data.decode('utf-8', 'ignore').splitlines():
                s = line.strip()
                if s.startswith('magnet:?'):
                    out.append(s)
        except Exception:
            pass
        return out

    def _load(self, extend):
        mags = []
        # 1) ext 指定的 txt
        if isinstance(extend, str) and extend.strip().lower().endswith('.txt'):
            mags = self._from_txt(extend.strip())
        # 2) 本 py 同目录的 txt(可多个,合并)
        if not mags:
            try:
                d = os.path.dirname(os.path.abspath(__file__))
                for fn in sorted(os.listdir(d)):
                    if fn.lower().endswith('.txt'):
                        mags.extend(self._from_txt(os.path.join(d, fn)))
            except Exception:
                pass
        # 3) 内置列表
        if not mags:
            mags = list(self.EMBEDDED)
        # 去重保序
        seen = set()
        uniq = []
        for m in mags:
            if m not in seen:
                seen.add(m)
                uniq.append(m)
        self.items = uniq

    def _name(self, idx, magnet):
        h = magnet
        try:
            h = magnet.split('btih:', 1)[1].split('&', 1)[0]
        except Exception:
            pass
        return '磁力 %03d · %s' % (idx + 1, h[:10].upper())

    def _vod(self, idx, magnet):
        return {
            'vod_id': str(idx),
            'vod_name': self._name(idx, magnet),
            'vod_pic': '',
            'vod_remarks': 'magnet',
            'style': {'type': 'list'},
        }

    # ---------- TVBox 接口 ----------（注意:FongMi 的 Chaquopy 桥要 dict,不要 json 字符串）
    def _ensure(self):
        if not self.items:
            self._load('')

    def init(self, extend=''):
        self._load(extend)
        return ''

    def homeContent(self, filter=False):
        self._ensure()
        return {
            'class': [{'type_id': 'all', 'type_name': '全部磁力(%d)' % len(self.items)}],
            'list': [self._vod(i, m) for i, m in enumerate(self.items)],
        }

    def homeVideoContent(self):
        self._ensure()
        return {'list': [self._vod(i, m) for i, m in enumerate(self.items)]}

    def categoryContent(self, tid, pg, filter=False, extend=None):
        self._ensure()
        try:
            page = int(pg)
        except Exception:
            page = 1
        size = 50
        total = len(self.items)
        start = (page - 1) * size
        chunk = self.items[start:start + size]
        return {
            'page': page,
            'pagecount': (total + size - 1) // size if total else 1,
            'limit': size,
            'total': total,
            'list': [self._vod(start + i, m) for i, m in enumerate(chunk)],
        }

    def detailContent(self, ids):
        self._ensure()
        vid = ids[0] if isinstance(ids, (list, tuple)) and ids else ids
        try:
            idx = int(vid)
        except Exception:
            idx = 0
        if idx < 0 or idx >= len(self.items):
            idx = 0
        magnet = self.items[idx]
        vod = {
            'vod_id': str(idx),
            'vod_name': self._name(idx, magnet),
            'vod_pic': '',
            'vod_content': magnet,
            'vod_play_from': '磁力',
            'vod_play_url': '播放$' + magnet,
        }
        return {'list': [vod]}

    def playerContent(self, flag, id, vipFlags=None):
        return {'parse': 0, 'playUrl': '', 'url': id, 'header': {}}

    def searchContent(self, key, quick=False, pg='1'):
        self._ensure()
        key = (key or '').strip().lower()
        hits = []
        for i, m in enumerate(self.items):
            if not key or key in m.lower() or key in str(i + 1):
                hits.append(self._vod(i, m))
        return {'list': hits}

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return None
