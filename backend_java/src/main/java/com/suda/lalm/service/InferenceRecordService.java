package com.suda.lalm.service;

import com.suda.lalm.entity.InferenceRecord;
import com.suda.lalm.entity.User;
import com.suda.lalm.entity.UserFeedback;
import com.suda.lalm.repository.InferenceRecordRepository;
import com.suda.lalm.repository.UserFeedbackRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.Optional;

@Service
@RequiredArgsConstructor
@Slf4j
public class InferenceRecordService {

    private final InferenceRecordRepository recordRepository;
    private final UserFeedbackRepository feedbackRepository;

    @Transactional
    public InferenceRecord saveRecord(User user, String prompt, String asr, Map<String, Object> result) {
        InferenceRecord record = new InferenceRecord();
        record.setUser(user);
        record.setPromptText(prompt);
        record.setAsrText(asr);
        
        // 从模型返回结果中提取字段
        if (result != null) {
            record.setRawReasoning((String) result.get("reasoning"));
            record.setFinalAnswer((String) result.get("answer"));
            
            Object score = result.get("difficulty_score");
            if (score instanceof Number) {
                record.setDifficultyScore(((Number) score).intValue());
            }
            
            record.setDifficultyStatus((String) result.get("difficulty_status"));
            
            Object time = result.get("execution_time");
            if (time instanceof Number) {
                record.setExecutionTime(((Number) time).doubleValue());
            }
        }
        
        record.setCreatedAt(LocalDateTime.now());
        return recordRepository.save(record);
    }

    public List<InferenceRecord> getUserHistory(User user) {
        return recordRepository.findByUserOrderByCreatedAtDesc(user);
    }

    @Transactional
    public UserFeedback saveFeedback(Long recordId, Integer rating, String comment) {
        InferenceRecord record = recordRepository.findById(recordId)
                .orElseThrow(() -> new RuntimeException("Inference record not found"));
        
        UserFeedback feedback = feedbackRepository.findByRecord(record)
                .orElse(new UserFeedback());
        
        feedback.setRecord(record);
        feedback.setRating(rating);
        feedback.setComment(comment);
        feedback.setCreatedAt(LocalDateTime.now());
        
        return feedbackRepository.save(feedback);
    }
}
