import json
import time
import types
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.lighthouse.v20200324 import lighthouse_client, models

try:
    # 实例化一个认证对象，入参需要传入腾讯云账户 SecretId 和 SecretKey，此处还需注意密钥对的保密
    # 代码泄露可能会导致 SecretId 和 SecretKey 泄露，并威胁账号下所有资源的安全性。以下代码示例仅供参考，建议采用更安全的方式来使用密钥，请参见：https://cloud.tencent.com/document/product/1278/85305
    # 密钥可前往官网控制台 https://console.cloud.tencent.com/cam/capi 进行获取
    cred = credential.Credential("xxx", "xxx")
    # 实例化一个http选项，可选的，没有特殊需求可以跳过
    httpProfile = HttpProfile()
    httpProfile.endpoint = "lighthouse.tencentcloudapi.com"

    # 实例化一个client选项，可选的，没有特殊需求可以跳过
    clientProfile = ClientProfile()
    clientProfile.httpProfile = httpProfile
    # 实例化要请求产品的client对象,clientProfile是可选的
    client = lighthouse_client.LighthouseClient(cred, "ap-singapore", clientProfile)

    instance_list = ['lhins-eww0iqkv', 'lhins-ey4yuekr', 'lhins-1nwuj0z1', 'lhins-m97eu5ux', 'lhins-nouvpn0r',
                     'lhins-g0doefup', 'lhins-iw4k0g31', 'lhins-de372z7p', 'lhins-m1d0knfv', 'lhins-f9z5dsnd',
                     'lhins-2f0ida9x', 'lhins-72gjhlfv', 'lhins-ikrz89yj', 'lhins-8swmfm3r', 'lhins-2f8ns7vv',
                     'lhins-dlrhfpur', 'lhins-fogo6usp', 'lhins-7tbu48rt', 'lhins-cuuokemd', 'lhins-gki27b3d',
                     'lhins-jbzczl61', 'lhins-q0o75qbv', 'lhins-owp60ahv', 'lhins-9kfntqnd', 'lhins-191tu3cz',
                     'lhins-95elnhu1', 'lhins-qnmdokyp', 'lhins-5ua9w56r', 'lhins-kini79wj', 'lhins-9grjjtl7',
                     'lhins-mt7qprz5', 'lhins-dlpxjtjj', 'lhins-jfxivjs3', 'lhins-55vuusqt', 'lhins-6igxeo8x',
                     'lhins-av5o830r', 'lhins-qvy6gz4z', 'lhins-hzkafo4n', 'lhins-lqahl2mj', 'lhins-mxpaz9k5',
                     'lhins-f5roptf3', 'lhins-ga046h2n', 'lhins-4ets7z2n', 'lhins-65wk1uoz', 'lhins-bulka42z',
                     'lhins-rio2zkmb', 'lhins-bvc9ryn5', 'lhins-m1lsg2o1', 'lhins-34ednhwl', 'lhins-0hh4j6h7',
                     'lhins-eudnyikr', 'lhins-52gmjc25', 'lhins-du63rdc9', 'lhins-9c436i9z', 'lhins-oa0b6cu9',
                     'lhins-2v0e4v9h', 'lhins-c2j6i4ml', 'lhins-kmiv1j2f', 'lhins-1t10drad', 'lhins-jyxs8w95',
                     'lhins-glqxmzor', 'lhins-dpw7r71d', 'lhins-pkcgec69', 'lhins-7u3hsew3', 'lhins-3qbhcgkr',
                     'lhins-ntano8rv', 'lhins-5lxak0fh', 'lhins-d6ghe8g3', 'lhins-4e9aqy5l', 'lhins-05tmuekn',
                     'lhins-2fayd5nx', 'lhins-jvmvahsb', 'lhins-ozw4rrdv', 'lhins-i4rxg22t', 'lhins-brfq56rv',
                     'lhins-qsrr90fh', 'lhins-fsw1dykl', 'lhins-0pah72wb', 'lhins-qs187en9', 'lhins-a503q89t',
                     'lhins-ldpnwdgn', 'lhins-krgg50ir', 'lhins-g0cqfo3n', 'lhins-dr5qxhnz', 'lhins-7i8x2955',
                     'lhins-6tckndtz', 'lhins-o4cs8udd', 'lhins-rj7c42x3', 'lhins-qjw86vmz', 'lhins-p4v8ec77',
                     'lhins-nicp0ru1', 'lhins-2goci5ah', 'lhins-iwfkwjor', 'lhins-f8zrzkth', 'lhins-b7hnii8b',
                     'lhins-hrffszgn', 'lhins-a4xuqh59', 'lhins-01m69v1d', 'lhins-eoxt9arr', 'lhins-1zxsfbs9',
                     'lhins-pju0578p', 'lhins-hkk1d2mf', 'lhins-fl02emff', 'lhins-9gclpp9d', 'lhins-3mej4gg3',
                     'lhins-e3291qud', 'lhins-eap1lhyd', 'lhins-6lnnr007', 'lhins-p9jdp78t', 'lhins-okv2yw87',
                     'lhins-gxkei5sz', 'lhins-2bc9qx7v', 'lhins-rsbwx3bh', 'lhins-lexi1x0h', 'lhins-l2ts5nrh',
                     'lhins-nkvu8med', 'lhins-irik02lh', 'lhins-f1rxgow9', 'lhins-hcn9fvfn', 'lhins-61yltqqt',
                     'lhins-lxw1z5jb', 'lhins-1jocb2tj', 'lhins-e6rxk47f', 'lhins-hc7qupz7', 'lhins-901mbpt9',
                     'lhins-1r9tjber', 'lhins-s084zd49', 'lhins-oth977kd', 'lhins-hwdlemp1', 'lhins-pdghb759',
                     'lhins-2vj6ox0v', 'lhins-igez3bb5', 'lhins-c77zg6ff', 'lhins-88unvi93', 'lhins-g5pbjt9f',
                     'lhins-inrr1eox', 'lhins-8c3uon61', 'lhins-mljgunqb', 'lhins-1z85qx6p', 'lhins-b7yr7l59',
                     'lhins-nxod63pj', 'lhins-7teoi2xt', 'lhins-ovzjfoav', 'lhins-i7q11rqn', 'lhins-lz79dqdf',
                     'lhins-5hpxxq5p', 'lhins-dxboingn', 'lhins-4a4lo025', 'lhins-l3javhpn', 'lhins-46kyuyqx',
                     'lhins-dn79yrk1', 'lhins-2c1dqc6d', 'lhins-8x2caocl', 'lhins-0vzcms0x', 'lhins-lxxb0mof',
                     'lhins-80apmko7', 'lhins-7djhkamh', 'lhins-pghovksh', 'lhins-1fg96ae9', 'lhins-1kw44t8l',
                     'lhins-0chd3vux', 'lhins-di3h7ctd', 'lhins-9wlkivv1', 'lhins-6mdvvaqt', 'lhins-q8cyzasr',
                     'lhins-oc71nbjf', 'lhins-n5l6ogjt', 'lhins-bmhlvfv3', 'lhins-33nrwrs9', 'lhins-dycdfte7',
                     'lhins-mlacaay3', 'lhins-q0xmpl8l', 'lhins-n2mbjkj1', 'lhins-d1supzdx', 'lhins-4b0prlz7',
                     'lhins-7q75ldm5', 'lhins-nhuwpr6r', 'lhins-ktwneajv', 'lhins-kn9ajt0h', 'lhins-97pt5tt3',
                     'lhins-n59iw8xz', 'lhins-mt9xrr4f', 'lhins-5e8ljwa7', 'lhins-gltlykgx', 'lhins-mxn1q19h',
                     'lhins-2bti8ayz', 'lhins-b41adq5j', 'lhins-goq41on5', 'lhins-0ruhax5t', 'lhins-rc98fbbh',
                     'lhins-duujumqt', 'lhins-hs9fjc95', 'lhins-8gszu83v', 'lhins-rb1x1gq7', 'lhins-0xfi7j9h',
                     'lhins-573hwje3', 'lhins-f1u977l1', 'lhins-aniibhvl', 'lhins-4yars27h', 'lhins-jqr20y81',
                     'lhins-olcmlz9r', 'lhins-ibfmdner', 'lhins-8ghu1hjj', 'lhins-3r3uw4kj', 'lhins-m70jb5ij',
                     'lhins-89uqhvvr', 'lhins-3mdy2orz', 'lhins-cvmblu7j', 'lhins-47du33ab', 'lhins-1jx5ma23',
                     'lhins-5y10zegf', 'lhins-h97j92q1', 'lhins-4eb383z9', 'lhins-dufk964l', 'lhins-gdvsk44n',
                     'lhins-6pc9alqd', 'lhins-jzn8x7pf', 'lhins-8x0dgi8z', 'lhins-0wsut5vp', 'lhins-008nes6d',
                     'lhins-lqq37t0r', 'lhins-69nktbj7', 'lhins-f6fikl0j', 'lhins-o4khhix1', 'lhins-69wt9v6p',
                     'lhins-esxzhfwj', 'lhins-p4l6pfz7', 'lhins-i0tz1k3v', 'lhins-10g620kh', 'lhins-2vt96wlj',
                     'lhins-465uesh9', 'lhins-lv591mx3', 'lhins-97w1ddah', 'lhins-mphwgvt5', 'lhins-cna55esn',
                     'lhins-px88gzv3', 'lhins-4abaqjux', 'lhins-3k8tahc1', 'lhins-909grsi7', 'lhins-pbqbf1t7',
                     'lhins-dadksizr', 'lhins-l3b1ux1n', 'lhins-e1zzub65', 'lhins-2k5sg0r3', 'lhins-8h0wziq5',
                     'lhins-cvdmjgbv', 'lhins-rusaf1z5', 'lhins-9t5qwhpj', 'lhins-88meau75', 'lhins-05lsfejn',
                     'lhins-n5tnbdr7', 'lhins-dy31wd1j', 'lhins-hop7vgrp', 'lhins-oxe1agy7', 'lhins-2c19ziv5',
                     'lhins-i8xva5xn', 'lhins-3b3ahnn1', 'lhins-b7gjhnep', 'lhins-5dtkoz2l', 'lhins-rrqrg6hv',
                     'lhins-7lg61m19', 'lhins-i7h7zt43', 'lhins-g8fayve7', 'lhins-dacvd83t', 'lhins-b85nrfdb',
                     'lhins-l3m6lbtb', 'lhins-cbfg4ww3', 'lhins-7gqea62z', 'lhins-9ftri1l1', 'lhins-an09ekfd',
                     'lhins-61wxyaq7', 'lhins-kio639zj', 'lhins-ispwzeav', 'lhins-ar765mvf', 'lhins-bc2jbkg1',
                     'lhins-90s3bxu3', 'lhins-mxxyy99n', 'lhins-bfcqwnz7', 'lhins-pzhd8rd5', 'lhins-owyp7n1j',
                     'lhins-iuw3e4i1', 'lhins-95i3r8pz', 'lhins-0ojz0lfl', 'lhins-qrag8ix9', 'lhins-oc8rxvcb',
                     'lhins-79e8vmf9', 'lhins-lqqkisxz', 'lhins-90teb05r', 'lhins-9h89g421', 'lhins-n24bcbcd',
                     'lhins-2jy22a31', 'lhins-igc4j7c9', 'lhins-bc3jo1zd', 'lhins-094f7mq7', 'lhins-8h2i6xhj',
                     'lhins-9k8ksm9t', 'lhins-lqiso695', 'lhins-9reidw05', 'lhins-ocyfsnij', 'lhins-0wjwt8pz',
                     'lhins-79l1rj7r', 'lhins-pp0lkn6x', 'lhins-d7gr8te1', 'lhins-5f1y3wmn', 'lhins-o1fq9fzj',
                     'lhins-jv5sivtt', 'lhins-1o5692y1', 'lhins-poty8l7z', 'lhins-5i755rkx', 'lhins-ayskjzdt',
                     'lhins-j7yhjy8b', 'lhins-n1o8b8g3', 'lhins-dyryambn', 'lhins-q4l1p5z9', 'lhins-j3swm9jj',
                     'lhins-1zi5ki3z', 'lhins-dtvfzbet', 'lhins-j8hwzwjt', 'lhins-raqrx5hf', 'lhins-fcm6nnnp',
                     'lhins-bqdijedj', 'lhins-aof8welr', 'lhins-jqr5m78r', 'lhins-ognkw1f1', 'lhins-0pjsrdj5',
                     'lhins-pld3anm5', 'lhins-ktzvbqg1', 'lhins-75q5diej', 'lhins-1g7wg5if', 'lhins-1jz8p0a1',
                     'lhins-62ieomfh', 'lhins-044mhn6v', 'lhins-io7pblpn', 'lhins-5hxqn70p', 'lhins-6xq4u0gb',
                     'lhins-3f8z6i27', 'lhins-rmoe24ud', 'lhins-j7gbre8d', 'lhins-el0pic7d', 'lhins-1buedebp',
                     'lhins-cfjplr0r', 'lhins-pl2e7g87', 'lhins-a8e5qoit', 'lhins-42qtjsqx', 'lhins-7od94ith',
                     'lhins-4bsj4yq7', 'lhins-fht59s27', 'lhins-7u1h2ov9', 'lhins-d2hfvnhn', 'lhins-g4zjuv1r',
                     'lhins-m9pnw7af', 'lhins-4z1fpkmh', 'lhins-h8x26mth', 'lhins-lxwplunf', 'lhins-8nwytk4p',
                     'lhins-gc6yaw89', 'lhins-6yc0mhdb', 'lhins-g89zy0ap', 'lhins-5ixoqig9', 'lhins-4yjoi0yx',
                     'lhins-qb8t19xr', 'lhins-hwen726l', 'lhins-9011f23z', 'lhins-n1vijfmr', 'lhins-c3icbw6b',
                     'lhins-qwry6e6b', 'lhins-qcrt86q3', 'lhins-9087nact', 'lhins-f1t2emtn', 'lhins-2v0hkcyx',
                     'lhins-9z8j2whb', 'lhins-okwrxo1x', 'lhins-7dv7syqz', 'lhins-3083f0h7', 'lhins-hos101qf',
                     'lhins-7ghoy6h1', 'lhins-ftnw3jfv', 'lhins-mdfk5ezn', 'lhins-lim0l97v', 'lhins-nic4xqqp',
                     'lhins-rnc5pdxj', 'lhins-hlalurep', 'lhins-bn0m33lz', 'lhins-n228wcv5', 'lhins-cqywqz1d',
                     'lhins-nhwlkoel', 'lhins-crnpsov9', 'lhins-e235rlcz', 'lhins-3bsoj3ol', 'lhins-k70kv6p9',
                     'lhins-i7gl7a19', 'lhins-8snszm6j', 'lhins-37t30fvn', 'lhins-i02uibyb', 'lhins-em0oe0sn',
                     'lhins-eiiy5ikv', 'lhins-qbzdbbet', 'lhins-nknjyhet', 'lhins-57elm43x', 'lhins-gs7hrsg9']

    for instance_id in instance_list:

        # 实例化一个请求对象,每个接口都会对应一个request对象
        req = models.ResetInstanceRequest()
        params = {
            "InstanceId": instance_id,
            "BlueprintId": "lhbp-qnuz61zs"
        }
        req.from_json_string(json.dumps(params))

        # 返回的resp是一个ResetInstanceResponse的实例，与请求对象对应
        resp = client.ResetInstance(req)
        # 输出json格式的字符串回包
        print(resp.to_json_string())
        time.sleep(1)



except TencentCloudSDKException as err:
    print(err)
