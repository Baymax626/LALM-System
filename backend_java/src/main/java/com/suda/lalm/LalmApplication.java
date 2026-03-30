package com.suda.lalm;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.scheduling.annotation.EnableAsync;
import org.springframework.web.client.RestTemplate;

@SpringBootApplication
@EnableAsync
public class LalmApplication {

    public static void main(String[] args) {
        SpringApplication.run(LalmApplication.class, args);
    }

    @Bean
    public RestTemplate restTemplate() {
        org.springframework.http.client.SimpleClientHttpRequestFactory factory = new org.springframework.http.client.SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(10000); // 10 seconds connect timeout
        factory.setReadTimeout(180000);   // 180 seconds read timeout for 4-stage pipeline
        return new RestTemplate(factory);
    }
}
