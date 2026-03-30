package com.suda.lalm.exception;

import com.suda.lalm.common.ApiResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.HttpRequestMethodNotSupportedException;
import org.springframework.web.servlet.resource.NoResourceFoundException;

@RestControllerAdvice
@Slf4j
public class GlobalExceptionHandler {

    @ExceptionHandler(HttpRequestMethodNotSupportedException.class)
    public ResponseEntity<ApiResponse<Void>> handleMethodNotSupported(HttpRequestMethodNotSupportedException e) {
        log.warn("Method not supported: {}", e.getMessage());
        return ResponseEntity.status(405)
                .body(ApiResponse.error(405, "请求方法不支持，请检查接口文档"));
    }

    @ExceptionHandler(NoResourceFoundException.class)
    public ResponseEntity<ApiResponse<Void>> handleNoResourceFound(NoResourceFoundException e) {
        log.warn("Static resource not found: {}", e.getMessage());
        return ResponseEntity.status(404)
                .body(ApiResponse.error(404, "资源未找到"));
    }

    @ExceptionHandler(ResourceAccessException.class)
    public ResponseEntity<ApiResponse<Void>> handleResourceAccessException(ResourceAccessException e) {
        log.error("Failed to connect to Python server: {}", e.getMessage());
        return ResponseEntity.status(503)
                .body(ApiResponse.error(503, "无法连接到大模型服务器，请联系管理员检查 Python 服务状态。"));
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<ApiResponse<Void>> handleException(Exception e) {
        log.error("Internal Server Error: ", e);
        return ResponseEntity.status(500)
                .body(ApiResponse.error(500, "服务器内部错误: " + e.getMessage()));
    }
}
