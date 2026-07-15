# Seedance 2.0 official source index

This file is an original routing note. It links to official Volcengine material but does not copy or redistribute the source documents.

## Official documents

- [创建视频生成任务 API（火山方舟官方 PDF）](https://eps-common-private-online.tos-cn-beijing.volces.com/cloud-doc/eps-doc-center-pdf/%E7%81%AB%E5%B1%B1%E6%96%B9%E8%88%9F_%E5%88%9B%E5%BB%BA%E8%A7%86%E9%A2%91%E7%94%9F%E6%88%90%E4%BB%BB%E5%8A%A1%20API_1782388936.pdf)
- [Doubao Seedance 2.0 系列提示词指南（火山方舟官方 PDF）](https://eps-common-private-online.tos-cn-beijing.volces.com/cloud-doc/eps-doc-center-pdf/%E7%81%AB%E5%B1%B1%E6%96%B9%E8%88%9F_Doubao%20Seedance%202.0%20%E7%B3%BB%E5%88%97%E6%8F%90%E7%A4%BA%E8%AF%8D%E6%8C%87%E5%8D%97_1780907195.pdf)
- [火山方舟文档中心](https://www.volcengine.com/docs/82379)
- [火山方舟 API Key 配置](https://www.volcengine.com/docs/82379/1399008)
- [火山方舟 API Key 控制台](https://console.volcengine.com/ark/region:ark+cn-beijing/apikey)

The two official PDF URLs returned HTTP 200 when checked on 2026-07-16. URLs and API behavior may change; search the official Ark documentation center by document title if a direct link expires.

## Original implementation quick reference

The workflow currently targets these operations:

- Create task: `POST https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks`
- Query task: `GET https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks/{id}`
- Authentication: `Authorization: Bearer $ARK_API_KEY`
- Image references use `role: reference_image` and are addressed in upload order as `图片1` through `图片n`.
- An eligible video reference uses `role: reference_video` and is addressed as `视频1`.
- Use the real Model ID or Endpoint ID configured in the user's Ark account; never infer one from an old example.
- Multimodal reference mode is separate from strict first-frame/last-frame mode.
- Generated video URLs are temporary; download accepted clips promptly.

The Skill's current verified snapshot treats Seedance 2.0 series clip duration as integer 4–15 seconds or `-1`, and allows up to 9 reference images plus supported video/audio references. These limits are volatile. Recheck the exact active endpoint before every production job.

## Revalidation checklist

Before changing a request template or making a billable call, verify:

1. Exact model or endpoint identifier.
2. Supported generation mode and reference-media count.
3. Duration, ratio, resolution, and audio support.
4. Face and real-person reference restrictions.
5. Current task statuses and response fields.
6. Rate limits, pricing, balance requirements, and output URL lifetime.

Do not commit API keys, signed URLs, private asset IDs, or account-specific endpoint IDs.
