package com.suda.lalm.service;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.util.Map;

@Service
@Slf4j
public class ModelService {

    @Value("${python.model.server.url}")
    private String pythonServerUrl;

    private final RestTemplate restTemplate;

    public ModelService(RestTemplate restTemplate) {
        this.restTemplate = restTemplate;
    }

    public Map<String, Object> callModel(String prompt, MultipartFile audioFile, int stage, String context) {
        log.info("Calling Python Model Server at: {} (Stage: {})", pythonServerUrl, stage);

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.MULTIPART_FORM_DATA);

        MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
        body.add("prompt", prompt);
        body.add("stage", String.valueOf(stage));
        body.add("context", context);

        if (audioFile != null && !audioFile.isEmpty()) {
            try {
                // 将上传的音频包装为资源，携带原始文件名，供 Python 端接收
                ByteArrayResource audioResource = new ByteArrayResource(audioFile.getBytes()) {
                    @Override
                    public String getFilename() {
                        return audioFile.getOriginalFilename();
                    }
                };
                // Python 端期望的字段名为 audio_file
                body.add("audio_file", audioResource);
            } catch (IOException e) {
                log.error("Error reading audio file", e);
                throw new RuntimeException("Failed to process audio file");
            }
        }

        HttpEntity<MultiValueMap<String, Object>> requestEntity = new HttpEntity<>(body, headers);

        try {
            // 将 multipart/form-data 转发到 Python /inference
            ResponseEntity<Map> response = restTemplate.postForEntity(pythonServerUrl, requestEntity, Map.class);
            return response.getBody();
        } catch (org.springframework.web.client.ResourceAccessException e) {
            log.error("Timeout or connection error calling Python server: {}", e.getMessage());
            throw new RuntimeException("模型推理超时，请尝试缩短录音时长或检查服务器负载。");
        } catch (Exception e) {
            log.error("Error calling Python server", e);
            throw new RuntimeException("模型服务调用失败: " + e.getMessage());
        }
    }
}
