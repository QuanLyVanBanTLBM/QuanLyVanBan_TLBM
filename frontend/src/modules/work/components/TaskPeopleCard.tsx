import React from 'react';
import { useTranslation } from '@i18n/translate';
import { useIsMobile } from '../hooks/useIsMobile';
import { Employee } from '../types/employee';
import { TaskDetail } from '../types/task';
import { employeeMeta } from './EmployeeSelect';

/**
 * Khối "Luồng xử lý" theo ảnh mẫu của thầy: cây người liên quan, thứ tự cố định từ trên xuống.
 * "Lãnh đạo giao việc" là người tạo, "Phối hợp giải quyết" là cán bộ tham gia.
 */

interface TaskPeopleCardProps {
  task: TaskDetail;
  currentUserId: number | null;
}

interface FlowStep {
  label: string;
  icon: string;
  color: string;
  people: Employee[];
}

export default function TaskPeopleCard({ task, currentUserId }: TaskPeopleCardProps) {
  const { t } = useTranslation();
  const isMobile = useIsMobile();
  const steps: FlowStep[] = [
    { label: t('work.peopleCard.stepCreator'), icon: 'fa-solid fa-user-tie', color: 'var(--color-purple)', people: [task.creator] },
    { label: t('work.peopleCard.stepDirectors'), icon: 'fa-solid fa-eye', color: 'var(--color-info)', people: task.directors },
    {
      label: t('work.peopleCard.stepHost'),
      icon: 'fa-solid fa-user-check',
      color: 'var(--color-primary)',
      people: task.host ? [task.host] : [],
    },
    { label: t('work.peopleCard.stepParticipants'), icon: 'fa-solid fa-users', color: 'var(--color-success)', people: task.participants },
  ];

  return (
    <section
      style={{
        background: 'var(--bg-surface)',
        border: '1px solid var(--border-subtle)',
        borderRadius: 'var(--radius-xl)',
        padding: isMobile ? '14px 14px' : '18px 20px',
        boxShadow: 'var(--shadow-sm)',
      }}
    >
      <h2 style={{ fontSize: '1rem', fontWeight: 800, color: 'var(--text-main)', marginBottom: '16px' }}>
        <i className="fa-solid fa-sitemap" style={{ color: 'var(--color-primary)', marginRight: '8px' }} />
        {t('work.peopleCard.heading')}
      </h2>

      <ol style={{ listStyle: 'none', position: 'relative' }}>
        {steps.map((step, index) => {
          const isLast = index === steps.length - 1;
          return (
            <li key={step.label} style={{ position: 'relative', paddingLeft: '40px', paddingBottom: isLast ? 0 : '18px' }}>
              {!isLast && (
                <span
                  aria-hidden="true"
                  style={{
                    position: 'absolute',
                    left: '15px',
                    top: '32px',
                    bottom: '0',
                    width: '2px',
                    background: 'var(--border-subtle)',
                  }}
                />
              )}
              <span
                aria-hidden="true"
                style={{
                  position: 'absolute',
                  left: 0,
                  top: 0,
                  width: '32px',
                  height: '32px',
                  borderRadius: 'var(--radius-full)',
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  background: 'var(--bg-surface-hover)',
                  border: `2px solid ${step.color}`,
                  color: step.color,
                  fontSize: '0.8rem',
                }}
              >
                <i className={step.icon} />
              </span>

              <div style={{ fontSize: '0.8rem', fontWeight: 700, color: step.color, lineHeight: '32px' }}>{step.label}</div>

              {step.people.length === 0 ? (
                <div style={{ fontSize: '0.84rem', color: 'var(--text-muted)' }}>{t('work.common.none')}</div>
              ) : (
                <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  {step.people.map((person) => (
                    <li key={`${step.label}-${person.id}`} style={{ fontSize: '0.86rem', color: 'var(--text-main)' }}>
                      <span style={{ fontWeight: 600 }}>{person.fullName}</span>
                      {employeeMeta(person) && (
                        <span style={{ color: 'var(--text-secondary)' }}> ({employeeMeta(person)})</span>
                      )}
                      {person.id === currentUserId && (
                        <span
                          style={{
                            marginLeft: '6px',
                            padding: '0 6px',
                            borderRadius: 'var(--radius-full)',
                            background: 'var(--color-primary-subtle)',
                            border: '1px solid var(--color-primary-border)',
                            color: 'var(--color-primary)',
                            fontSize: '0.7rem',
                            fontWeight: 700,
                          }}
                        >
                          {t('work.common.you')}
                        </span>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </li>
          );
        })}
      </ol>
    </section>
  );
}
