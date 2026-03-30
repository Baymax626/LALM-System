package com.suda.lalm.repository;

import com.suda.lalm.entity.InferenceRecord;
import com.suda.lalm.entity.UserFeedback;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface UserFeedbackRepository extends JpaRepository<UserFeedback, Long> {
    Optional<UserFeedback> findByRecord(InferenceRecord record);
}
