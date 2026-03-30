package com.suda.lalm.entity;

import jakarta.persistence.*;
import lombok.Data;
import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "inference_records")
public class InferenceRecord {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "user_id", nullable = false)
    private User user;

    @Column(columnDefinition = "TEXT")
    private String asrText;

    @Column(columnDefinition = "TEXT")
    private String promptText;

    @Column(columnDefinition = "TEXT")
    private String rawReasoning;

    @Column(columnDefinition = "TEXT")
    private String finalAnswer;

    private Integer difficultyScore;

    @Column(length = 32)
    private String difficultyStatus;

    private Double executionTime;

    private LocalDateTime createdAt = LocalDateTime.now();
}
