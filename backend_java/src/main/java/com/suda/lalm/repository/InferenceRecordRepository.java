package com.suda.lalm.repository;

import com.suda.lalm.entity.InferenceRecord;
import com.suda.lalm.entity.User;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface InferenceRecordRepository extends JpaRepository<InferenceRecord, Long> {
    List<InferenceRecord> findByUserOrderByCreatedAtDesc(User user);
    Page<InferenceRecord> findByUser(User user, Pageable pageable);
}
