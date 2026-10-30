// Experimental, version-guarded FM24 initial-award-history correction.
// Changes one dispatch pointer in private process DATA, never executable bytes
// or installed files. Only the seventeen independently sourced editions are allowed.
#include <mach-o/dyld.h>
#include <mach-o/loader.h>
#include <mach/mach.h>
#include <mach/mach_vm.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdatomic.h>
#include <unistd.h>

__attribute__((visibility("hidden"))) uintptr_t fm24_native_get_manager;
__attribute__((visibility("hidden"))) uintptr_t fm24_native_cache_address;
__attribute__((visibility("hidden"))) uintptr_t fm24_native_continuation;
extern void fm24_continue_award_conversion(void *, void *, bool *, uint32_t);

typedef void (*conversion_dispatch)(void *, void **, bool *);
static conversion_dispatch original_dispatch;
static uint16_t (*native_history_info)(const void *, unsigned);
static FILE *audit;
static unsigned converted;
static void inspect_comp_history_source(const char *phase);

// Additional version-guarded observers for the four fixed-date awards whose
// evaluation windows remain in 2023/24 after the jump to 2026. Default: observe.
// "apply" is an explicit experimental launch option, not a release default.
typedef int (*year_loader)(void *, void *, void *);
typedef void (*manager_handler)(void *, void *);
static year_loader original_year_load;
static manager_handler original_manager_handler;
static void (*native_period_calculator)(void *);
static const uint16_t *native_current_date;
static uintptr_t year_vptr;
static unsigned schedule_observed, schedule_changed;
static int schedule_mode; // 0 disabled; 1 proposal only; 2 apply checked proposal
static unsigned manager_events, time_events;
static unsigned last_progress_date;
static bool recover_first_ceremony;

// All nineteen fixed-date definitions in the verified 24.3.0 native table.
// The live manager still decides which awards exist for the loaded nations.
static const uint32_t fixed_award_uids[] = {
    102406,106933,136350,136351,136352,150967,527303,7842996,
    16122531,19004986,19033877,23199360,37013148,89066985,
    2000005199,2000065456,2000133247,2000325760,2000325761
};
static struct {
    void *object;
    unsigned date, mode;
} schedule_attempts[sizeof fixed_award_uids/sizeof *fixed_award_uids];

static bool known_fixed_award(uint32_t uid) {
    for (size_t i=0;i<sizeof fixed_award_uids/sizeof *fixed_award_uids;++i)
        if (fixed_award_uids[i]==uid) return true;
    return false;
}

static uint16_t u16_at(const void *p, size_t offset) {
    uint16_t value;
    memcpy(&value, (const char *)p+offset, sizeof value);
    return value;
}

static unsigned date_key(const void *p, size_t offset) {
    unsigned year=u16_at(p,offset+2), day=u16_at(p,offset)&0x1ff;
    unsigned max_day=365+(year%4==0 && (year%100!=0 || year%400==0));
    return year>=1900 && year<=2101 && day>=1 && day<=max_day ? year*512+day : 0;
}

static bool stalled_fixed_award(void *object) {
    if (!object || !native_current_date || !native_period_calculator)
        return false;
    unsigned char *data = object;
    if (*(uintptr_t *)data != year_vptr || data[0x28] != 1)
        return false;
    unsigned char *award = *(unsigned char **)(data+8);
    if (!award || award[0x82] != 6)
        return false;
    uint32_t uid;
    memcpy(&uid, award+0x0c, sizeof uid);
    if (!known_fixed_award(uid))
        return false;
    uint16_t current_year = native_current_date[1];
    uint16_t day = native_current_date[0] & 0x1ff;
    uint16_t old_year = u16_at(data, 0x1e);
    if (current_year < 2026 || current_year > 2100 || day < 1 || day > 366 ||
        old_year < 2023 || old_year+1 >= current_year)
        return false;
    // A live candidacy/voting state is deliberately outside this first fix.
    // A fresh career has empty candidate data; don't silently reuse old votes.
    return *(uintptr_t *)(data+0x30) == *(uintptr_t *)(data+0x38) &&
           *(uintptr_t *)(data+0x48) == 0 && *(uintptr_t *)(data+0x50) == 0;
}

static unsigned days_in_year(unsigned y) {
    return 365+(y%4==0 && (y%100!=0 || y%400==0));
}

// SI_DATE stores calendar day-of-year, so a year shift must retain month/day,
// not the numeric ordinal across leap years. February 29 has no prior-year
// equivalent and is deliberately rejected by this first-cycle experiment.
static uint32_t prior_calendar_year(uint32_t encoded) {
    unsigned year=encoded>>16, day=encoded&0x1ff;
    if (year<2026 || year>2101 || day<1 || day>days_in_year(year)) return 0;
    if (days_in_year(year)==366) {
        if (day==60) return 0;
        if (day>60) day--;
    } else if (days_in_year(year-1)==366 && day>=60) day++;
    return ((year-1)<<16)|(encoded&0xfe00)|day;
}

static bool normalize_future_window(unsigned char *proposal) {
    unsigned now=native_current_date[1]*512+(native_current_date[0]&0x1ff);
    unsigned start=date_key(proposal,0x18),end=date_key(proposal,0x1c);
    if (!start || start<=now || end<=start || end-start<500 || end-start>525 ||
        u16_at(proposal,0x1a)!=native_current_date[1] ||
        u16_at(proposal,0x1e)!=native_current_date[1]+1 ||
        date_key(proposal,0x20)!=end) return false;
    uint32_t shifted[4];
    for (unsigned i=0;i<4;++i) {
        uint32_t original;
        memcpy(&original,proposal+0x18+4*i,4);
        shifted[i]=date_key(proposal,0x18+4*i)==1900*512+1 ? original :
                   prior_calendar_year(original);
        if (!shifted[i]) return false;
    }
    memcpy(proposal+0x18,shifted,sizeof shifted);
    return true;
}

static bool first_ceremony_proposal(unsigned char *proposal, const unsigned char *data) {
    if (!recover_first_ceremony) return false;
    unsigned year=native_current_date[1], day=native_current_date[0]&0x1ff;
    if (u16_at(proposal,0x1e)!=year+1 || u16_at(proposal,0x26)!=year+1)
        return false;
    uint32_t previous[4];
    for (unsigned i=0;i<4;++i) {
        uint32_t original;
        memcpy(&original,proposal+0x18+4*i,4);
        previous[i]=prior_calendar_year(original);
        if (!previous[i]) return false;
    }
    // Keep the nominal evaluation season. Move only its missed processing
    // deadline, as the native postponement path does (+1c vs original +20).
    // Nominations get their full configured lead time starting tomorrow.
    int16_t lead;
    memcpy(&lead,data+0x2a,2);
    if (lead<0 || lead>90) return false;
    unsigned trigger_day=day+(unsigned)lead+2;
    unsigned now_key=year*512+day;
    unsigned nominal_key=(previous[2]>>16)*512+(previous[2]&0x1ff);
    unsigned announcement_key=(previous[3]>>16)*512+(previous[3]&0x1ff);
    if (trigger_day>days_in_year(year) || nominal_key>=now_key ||
        (previous[2]>>16)!=year || announcement_key<=year*512+trigger_day)
        return false;
    previous[1]=(year<<16)|(previous[1]&0xfe00)|trigger_day;
    memcpy(proposal+0x18,previous,sizeof previous);
    return true;
}

static void inspect_schedule(void *object, const char *phase) {
    if (!schedule_mode || !stalled_fixed_award(object))
        return;
    unsigned char *data = object;
    unsigned char *award = *(unsigned char **)(data+8);
    uint32_t uid;
    memcpy(&uid, award+0x0c, sizeof uid);
    size_t index=0;
    while (index<sizeof fixed_award_uids/sizeof *fixed_award_uids &&
           fixed_award_uids[index]!=uid) index++;
    if (index==sizeof fixed_award_uids/sizeof *fixed_award_uids) return;
    unsigned current_date=native_current_date[1]*512+(native_current_date[0]&0x1ff);
    unsigned current_mode=(unsigned)schedule_mode*2+recover_first_ceremony;
    if (schedule_attempts[index].object==object &&
        schedule_attempts[index].date==current_date &&
        schedule_attempts[index].mode==current_mode) return;
    schedule_attempts[index].object=object;
    schedule_attempts[index].date=current_date;
    schedule_attempts[index].mode=current_mode;
    _Alignas(16) unsigned char proposal[0x58];
    memcpy(proposal, data, sizeof proposal);
    // Use the game's own period/date calculation on a temporary object. This
    // routine writes dates only and does not own/delete candidate pointers.
    native_period_calculator(proposal);
    bool normalized=normalize_future_window(proposal);
    uint16_t new_end_year = u16_at(proposal, 0x1e);
    unsigned end_day = u16_at(proposal, 0x1c) & 0x1ff;
    unsigned now_day = native_current_date[0] & 0x1ff;
    unsigned start_key=date_key(proposal,0x18), end_key=date_key(proposal,0x1c);
    unsigned announcement_key=date_key(proposal,0x24);
    unsigned current_key=native_current_date[1]*512+now_day;
    bool valid = (new_end_year == native_current_date[1] ||
                  new_end_year == native_current_date[1]+1) &&
                 end_day >= 1 && end_day <= 366 &&
                 start_key && start_key<=current_key && end_key>=current_key &&
                 end_key-start_key>=500 && end_key-start_key<=525 &&
                 date_key(proposal,0x20)==end_key &&
                 (announcement_key==1900*512+1 || announcement_key>=end_key) &&
                 memcmp(proposal, data, 0x18) == 0 &&
                 memcmp(proposal+0x28, data+0x28, sizeof proposal-0x28) == 0;
    bool first_cycle = valid && first_ceremony_proposal(proposal,data);
    if (audit) {
        fprintf(audit, "SCHEDULE_PROPOSAL phase=%s award=%u current=%u/%u old_end=%u/%u new_start=%u/%u new_end=%u/%u new_announcement=%u/%u valid=%u apply=%u first_cycle=%u nominal_end=%u/%u normalized=%u\n",
            phase, uid, native_current_date[1], now_day,
            u16_at(data,0x1e), u16_at(data,0x1c)&0x1ff,
            u16_at(proposal,0x1a),u16_at(proposal,0x18)&0x1ff,
            u16_at(proposal,0x1e),u16_at(proposal,0x1c)&0x1ff,
            u16_at(proposal,0x26),u16_at(proposal,0x24)&0x1ff,
            valid,valid && schedule_mode==2,first_cycle,
            u16_at(proposal,0x22),u16_at(proposal,0x20)&0x1ff,normalized);
        fflush(audit);
    }
    schedule_observed++;
    if (valid && schedule_mode == 2) {
        memcpy(data+0x18, proposal+0x18, 0x10);
        schedule_changed++;
    }
}

static int load_year(void *object, void *reader, void *context) {
    int result = original_year_load(object, reader, context);
    if (result && audit && object) {
        unsigned char *data=object;
        unsigned char *award=*(unsigned char **)(data+8);
        uint32_t uid=0;
        if (award) memcpy(&uid,award+0x0c,4);
        if (uid==102406 || uid==150967 || uid==89066985 || uid==2000065456) {
            fprintf(audit,"SCHEDULE_LOADED award=%u current=%u/%u old_end=%u/%u candidate_empty=%u voting_present=%u special_present=%u\n",
                uid,native_current_date[1],native_current_date[0]&0x1ff,
                u16_at(data,0x1e),u16_at(data,0x1c)&0x1ff,
                *(uintptr_t *)(data+0x30)==*(uintptr_t *)(data+0x38),
                *(uintptr_t *)(data+0x48)!=0,*(uintptr_t *)(data+0x50)!=0);
            fflush(audit);
        }
    }
    if (result) inspect_schedule(object, "load");
    return result;
}

static void manager_event(void *object, void *message) {
    struct pending_ceremony {
        unsigned char *object;
        unsigned char dates[0x10];
        uint32_t uid;
    } pending[sizeof fixed_award_uids/sizeof *fixed_award_uids];
    size_t pending_count=0;
    uint32_t type = 0;
    if (message) memcpy(&type, (char *)message+0x20, sizeof type);
    if (type==0x47465244U) memset(schedule_attempts,0,sizeof schedule_attempts);
    manager_events++;
    if (audit && manager_events<=8) {
        fprintf(audit,"MANAGER_EVENT type=%08x current=%u/%u\n",type,
            native_current_date[1],native_current_date[0]&0x1ff);
        fflush(audit);
    }
    if (schedule_mode && type == 0x4754494dU) { // GTIM: native time event
        time_events++;
        unsigned current_day=native_current_date[0]&0x1ff;
        unsigned current_key=native_current_date[1]*512+current_day;
        if (audit && current_day>=1 && current_day<=366 &&
            native_current_date[1]>=2026 && current_key!=last_progress_date &&
            (current_day==1 || current_day%14==0)) {
            fprintf(audit,"CALENDAR_PROGRESS current=%u/%u\n",
                native_current_date[1],current_day);
            fflush(audit);
            last_progress_date=current_key;
        }
        uintptr_t *first = *(uintptr_t **)((char *)object+0x18);
        uintptr_t *last = *(uintptr_t **)((char *)object+0x20);
        uintptr_t begin = (uintptr_t)first, end = (uintptr_t)last;
        if (begin && end >= begin && (end-begin)%sizeof(uintptr_t)==0 &&
            (end-begin)/sizeof(uintptr_t) < 10000) {
            if (audit && time_events<=2) {
                fprintf(audit,"SCHEDULE_TIME objects=%lu current=%u/%u\n",
                    (unsigned long)((end-begin)/sizeof(uintptr_t)),
                    native_current_date[1],native_current_date[0]&0x1ff);
                for (uintptr_t *p=first;p<last;++p) {
                    unsigned char *d=(unsigned char *)*p;
                    if (!d) continue;
                    unsigned char *award=*(unsigned char **)(d+8);
                    uint32_t uid=0;
                    if(award)memcpy(&uid,award+0x0c,4);
                    if(uid==102406 || uid==150967 || uid==89066985 || uid==2000065456)
                        fprintf(audit,"SCHEDULE_OBJECT award=%u vptr_ok=%u kind=%u period=%u end=%u/%u candidates_empty=%u votes=%u special=%u\n",
                            uid,*(uintptr_t *)d==year_vptr,d[0x28],award[0x82],
                            u16_at(d,0x1e),u16_at(d,0x1c)&0x1ff,
                            *(uintptr_t *)(d+0x30)==*(uintptr_t *)(d+0x38),
                            *(uintptr_t *)(d+0x48)!=0,*(uintptr_t *)(d+0x50)!=0);
                }
                fflush(audit);
            }
            for (uintptr_t *p=first; p<last; ++p) {
                inspect_schedule((void *)*p, "time");
                unsigned char *d=(unsigned char *)*p;
                unsigned now=native_current_date[1]*512+(native_current_date[0]&0x1ff);
                if (!recover_first_ceremony || schedule_mode!=2 || !d ||
                    *(uintptr_t *)d!=year_vptr || d[0x28]!=1 ||
                    native_current_date[1]<2026 ||
                    date_key(d,0x1c)!=now || date_key(d,0x20)>=now ||
                    date_key(d,0x24)<=now || u16_at(d,0x26)!=native_current_date[1] ||
                    pending_count>=sizeof pending/sizeof *pending) continue;
                unsigned char *award=*(unsigned char **)(d+8);
                uint32_t uid=0;
                if (award) memcpy(&uid,award+0x0c,4);
                if (!award || award[0x82]!=6 || !known_fixed_award(uid)) continue;
                pending[pending_count].object=d;
                pending[pending_count].uid=uid;
                memcpy(pending[pending_count].dates,d+0x18,0x10);
                pending_count++;
            }
        }
    }
    original_manager_handler(object, message);
    // The native daily handler recalculates the period after processing its
    // deadline. A postponed first deadline falls after the usual June date,
    // so that recalculation would overwrite the still-pending October event
    // with next year's dates. Preserve this year's pending date block until
    // its ceremony; retain all native candidate/voting/history changes.
    for (size_t i=0;i<pending_count;++i) {
        unsigned char *d=pending[i].object;
        uintptr_t *first=*(uintptr_t **)((char *)object+0x18);
        uintptr_t *last=*(uintptr_t **)((char *)object+0x20);
        uintptr_t begin=(uintptr_t)first,end=(uintptr_t)last;
        bool live=false;
        if (begin && end>=begin && (end-begin)%sizeof(uintptr_t)==0 &&
            (end-begin)/sizeof(uintptr_t)<10000)
            for (uintptr_t *p=first;p<last;++p)
                if (*p==(uintptr_t)d) {live=true;break;}
        if (!live || *(uintptr_t *)d!=year_vptr ||
            u16_at(d,0x22)<=native_current_date[1] ||
            u16_at(d,0x26)<=native_current_date[1]) continue;
        memcpy(d+0x18,pending[i].dates,0x10);
        if (audit) {
            fprintf(audit,"FIRST_CYCLE_KEEP_CEREMONY award=%u deadline=%u/%u ceremony=%u/%u candidates=%lu\n",
                pending[i].uid,u16_at(d,0x1e),u16_at(d,0x1c)&0x1ff,
                u16_at(d,0x26),u16_at(d,0x24)&0x1ff,
                (unsigned long)((*(uintptr_t *)(d+0x38)-*(uintptr_t *)(d+0x30))/8));
            fflush(audit);
        }
    }
}

// Event registration uses the manager's second base subobject. Its native
// thunk subtracts eight and tail-calls the primary implementation directly,
// bypassing the primary vtable entry. Preserve that exact adjustment.
static void manager_secondary_event(void *subobject, void *message) {
    manager_event((unsigned char *)subobject-8, message);
}

static bool permitted(uint32_t award, uint16_t year) {
    return ((award == 102406 || award == 89066985 || award == 2000065456) &&
            (year == 2024 || year == 2025)) ||
           ((award == 102407 || award == 13197490) &&
            (year == 2023 || year == 2024 || year == 2025)) ||
           (award == 29108422 && (year == 2023 || year == 2024 || year == 2025)) ||
           (award == 2000180166 && (year == 2024 || year == 2025 || year == 2026));
}

static uint32_t ceremony_date(uint32_t award, uint16_t year) {
    // Source edition and ceremony year are distinct (FIFA 2023: 15/01/2024).
    // Native SI_DATE = 16-bit day-of-year followed by 16-bit calendar year.
    bool france_football=award==102406 || award==89066985 || award==2000065456;
    if (france_football && year==2024) return 2024U*65536+302; // 28/10/2024
    if (france_football && year==2025) return 2025U*65536+265; // 22/09/2025
    bool fifa=award==102407 || award==13197490;
    if (fifa && year==2023) return 2024U*65536+15;  // 15/01/2024
    if (fifa && year==2024) return 2024U*65536+352; // 17/12/2024
    if (fifa && year==2025) return 2025U*65536+350; // 16/12/2025
    // Additional facts: Tuttosport's 2023 event and announced 2024 ceremony;
    // UEFA's dated Player of the Season announcements. They define the age
    // displayed for that result, rather than the new career's current date.
    if (award==29108422 && year==2023) return 2023U*65536+338; // 04/12/2023
    if (award==29108422 && year==2024) return 2024U*65536+351; // 16/12/2024
    if (award==29108422 && year==2025) return 2025U*65536+335; // 01/12/2025
    if (award==2000180166 && year==2024) return 2024U*65536+155; // 03/06/2024
    if (award==2000180166 && year==2025) return 2025U*65536+152; // 01/06/2025
    if (award==2000180166 && year==2026) return 2026U*65536+151; // 31/05/2026
    return 0;
}

static bool retain_ballot_vote_info(const void *row, unsigned char *award,
                                    uint32_t uid, uint16_t year) {
    if (award[0x80]!=1 || !native_history_info) return false;
    static const uint16_t votes24[]={1170,1129,917},votes25[]={1380,1059,703};
    static const uint16_t kopa24[]={113,26,20},kopa25[]={124,72,23};
    static const uint16_t yashin24[]={276,213,112},yashin25[]={486,120,112};
    static const uint16_t fifa_gk23[]={23,20,16},fifa_gk24[]={26,16,13},fifa_gk25[]={28,20,9};
    static const uint16_t golden_boy23[]={485,285,92},golden_boy24[]={488,114,88};
    static const uint16_t golden_boy25[]={450,163,161};
    const uint16_t *expected=NULL;
    if (uid==102406) expected=year==2024?votes24:year==2025?votes25:NULL;
    if (uid==89066985) expected=year==2024?kopa24:year==2025?kopa25:NULL;
    if (uid==2000065456) expected=year==2024?yashin24:year==2025?yashin25:NULL;
    if (uid==13197490) expected=year==2023?fifa_gk23:year==2024?fifa_gk24:year==2025?fifa_gk25:NULL;
    if (uid==29108422) expected=year==2023?golden_boy23:year==2024?golden_boy24:year==2025?golden_boy25:NULL;
    if (!expected) return false;
    uint16_t values[3];
    for (unsigned i=0;i<3;++i) values[i]=native_history_info(row,i);
    bool match=memcmp(values,expected,sizeof values)==0;
    if (audit) {
        fprintf(audit,"HISTORY_VOTE_SOURCE award=%u edition=%u values=%u/%u/%u factual_match=%u\n",
            uid,year,values[0],values[1],values[2],match);
        fflush(audit);
    }
    return match;
}

static void dispatch(void *self, void **reference, bool *remove) {
    unsigned char *row = reference ? *reference : NULL;
    if (row && remove) {
        unsigned char *award = *(unsigned char **)(row + 0x18);
        uint16_t year;
        memcpy(&year, row + 0x8c, sizeof year);
        if (award && !row[0x9d] && year) {
            unsigned char *detail = *(unsigned char **)(award + 0x70);
            uint32_t uid;
            memcpy(&uid, award + 0x0c, sizeof uid);
            if (detail && (detail[0x28] == 1 || detail[0x28] == 4) && permitted(uid, year)) {
                if (!converted) inspect_comp_history_source("first_award_conversion");
                if (audit) {
                    fprintf(audit, "CONVERT award=%u edition=%u sequence=%u\n", uid, year, ++converted);
                    fflush(audit);
                }
                // The native converter discards AH1i/2i/3i for awards configured
                // as No Voting (+80 == 1). Use its existing voted-award import
                // branch only while importing these verified factual rows,
                // then restore the original future-selection configuration.
                unsigned char voting=award[0x80];
                bool retain_votes=retain_ballot_vote_info(row,award,uid,year);
                if (retain_votes) award[0x80]=7;
                fm24_continue_award_conversion((unsigned char *)self + 8, row, remove,
                                               ceremony_date(uid,year));
                if (retain_votes) {
                    award[0x80]=voting;
                    if (audit) {
                        fprintf(audit,"HISTORY_VOTE_MODE_RESTORED award=%u edition=%u mode=%u\n",uid,year,voting);
                        fflush(audit);
                    }
                }
                return;
            }
        }
    }
    original_dispatch(self, reference, remove);
}

// Optional read-only diagnosis of the source competition table. The hook
// forwards the original initializer unchanged and observes just World Cup
// records. It neither supplies results nor changes a competition/save.
static uintptr_t comp_history_table_address;
static uintptr_t comp_history_database_date_address;
static uintptr_t world_cup_source_owner;
static unsigned char world_cup_factual_history[0x60];
static bool world_cup_fact_admitted;
static bool world_cup_generation_ready;
static unsigned world_cup_generation;
static int world_cup_history_mode; // 0 disabled, 1 observe, 2 skip completed edition
static unsigned world_cup_policy_observations;
static bool (*original_world_cup_policy)(void *,const void *);
static void (*original_comp_history_init)(void *, unsigned);
static void (*original_comp_history_wrapper)(void *, uintptr_t);
static void (*original_comp_history_finalize)(void *);
static void (*original_comp_manager_init)(void *);
static bool comp_history_diagnostics;
static int international_history_mode;
static bool national_generation_ready;
typedef struct {
    uint32_t uid;
    uint16_t game_year,history_year,final_day,final_year;
    uint32_t podium[3];
} national_fact;
// Game-year mapping was observed in the actual 2026-start career. It is
// deliberately different from the history/final year for Asia and Africa.
static const national_fact national_facts[]={
    {1301389,2024,2024,196,2024,{1649,1653,1657}},
    {1301387,2024,2024,222,2024,{796,769,34}},
    {102414,2023,2024,41,2024,{132,117,0}},
    {1301390,2023,2024,42,2024,{24,38,45}},
    {1301390,2025,2026,18,2026,{34,41,38}}
};
#define NATIONAL_FACT_COUNT (sizeof national_facts/sizeof national_facts[0])
static uintptr_t national_fact_owners[NATIONAL_FACT_COUNT];
static unsigned national_skip_observations[NATIONAL_FACT_COUNT];
static void admit_national_facts_from_source(void);
// Isolated six-edition source-admitted bounded canary, not a source rewrite.
static int international6_mode;
static intptr_t international6_slide;
static void international6_reset(void);
static void international6_admit(void *manager);
static void international6_linked(void *manager);
// The policy input/result types are defined by the isolated core below.
static bool international6_install(intptr_t slide);
static bool writable_data_pointer(uintptr_t address,uintptr_t replacement);

static void reset_world_cup_generation(void) {
    international6_reset();
    world_cup_generation_ready=false;
    world_cup_fact_admitted=false;
    world_cup_source_owner=0;
    memset(world_cup_factual_history,0,sizeof world_cup_factual_history);
    world_cup_policy_observations=0;
    national_generation_ready=false;
    memset(national_fact_owners,0,sizeof national_fact_owners);
    memset(national_skip_observations,0,sizeof national_skip_observations);
    ++world_cup_generation;
}

static void observe_comp_manager_init(void *self) {
    // A new database may reuse the previous database's heap addresses.
    // Invalidate before the native manager releases/recreates its objects.
    reset_world_cup_generation();
    original_comp_manager_init(self);
}

static bool readable_copy(void *to, const void *from, size_t length) {
    if (!from) return false;
    mach_vm_size_t copied=0;
    kern_return_t result=mach_vm_read_overwrite(mach_task_self(),(mach_vm_address_t)from,
        length,(mach_vm_address_t)to,&copied);
    return result==KERN_SUCCESS && copied==length;
}

#include "international6_bounded_core.inc"

// Read-only probes for the other national tournaments. Each ABI is
// bool(GAME_COMP*); every wrapper always returns the exact native result.
typedef bool (*national_year_policy)(void *);
static national_year_policy original_national_policies[6];
static unsigned national_policy_observations[6];
static const uint32_t national_competition_uids[]={1301390,102414,1301389,1301388,1301387,90};
static national_year_policy original_actual_comp_policy;
static unsigned actual_policy_observations[6];

static bool completed_national_result(void *self,bool native) {
    if (!international_history_mode || !national_generation_ready) return native;
    uintptr_t source=0,database=0;uint32_t uid=0;uint16_t year=0,today[2]={0};
    if (!readable_copy(&source,(char *)self+0x138,8) || !source ||
        !readable_copy(&uid,(void *)(source+0xc),4) ||
        !readable_copy(&year,(char *)self+0x248,2) || !comp_history_database_date_address ||
        !readable_copy(&database,(void *)comp_history_database_date_address,8) || !database ||
        !readable_copy(today,(void *)(database+0x144),4) || today[1]!=2026) return native;
    for (unsigned k=0;k<NATIONAL_FACT_COUNT;++k) {
        const national_fact *f=&national_facts[k];
        if (uid!=f->uid || year!=f->game_year || source!=national_fact_owners[k] ||
            today[1]<f->final_year || (today[1]==f->final_year && (today[0]&511)<=f->final_day)) continue;
        bool skip=international_history_mode==2;
        if (audit && national_skip_observations[k]++<8) {
            fprintf(audit,"NATIONAL_COMPLETED_POLICY uid=%u game_year=%u history_year=%u native=%u skip_completed=%u\n",
                uid,year,f->history_year,native,skip);fflush(audit);
        }
        return skip?false:native;
    }
    return native;
}

static bool observe_actual_comp_policy(void *self) {
    uintptr_t international6_caller=(uintptr_t)__builtin_return_address(0);
    international6_policy_input international6_before=international6_policy_read(self);
    bool native=original_actual_comp_policy(self);
    bool result=completed_national_result(self,native);
    result=international6_result(self,result,0,international6_caller,&international6_before);
    uintptr_t source=0;uint32_t uid=0;uint16_t year=0;
    if (!audit || !comp_history_diagnostics ||
        !readable_copy(&source,(char *)self+0x138,8) || !source ||
        !readable_copy(&uid,(void *)(source+0xc),4) ||
        !readable_copy(&year,(char *)self+0x248,2)) return result;
    for (unsigned k=0;k<6;++k) if (uid==national_competition_uids[k] &&
            actual_policy_observations[k]++<24) {
        fprintf(audit,"ACTUAL_COMP_YEAR_POLICY uid=%u game_year=%u native=%u returned=%u\n",uid,year,native,result);
        fflush(audit);break;
    }
    return result;
}

static bool observe_national_policy(void *self,unsigned index) {
    bool result=original_national_policies[index](self);
    if (!audit || !comp_history_diagnostics || national_policy_observations[index]>=24) return result;
    uintptr_t source=0;uint32_t uid=0;uint16_t year=0;
    if (!readable_copy(&source,(char *)self+0x138,8) || !source ||
        !readable_copy(&uid,(void *)(source+0xc),4) || uid!=national_competition_uids[index] ||
        !readable_copy(&year,(char *)self+0x248,2) || year<2023 || year>2030) return result;
    ++national_policy_observations[index];
    fprintf(audit,"NATIONAL_YEAR_POLICY uid=%u game_year=%u native=%u data_changes=0\n",uid,year,result);
    fflush(audit);
    return result;
}

#define NATIONAL_POLICY_PROBE(number) \
    static bool national_policy_probe_##number(void *self) {return observe_national_policy(self,number);}
NATIONAL_POLICY_PROBE(0)
NATIONAL_POLICY_PROBE(1)
NATIONAL_POLICY_PROBE(2)
NATIONAL_POLICY_PROBE(3)
NATIONAL_POLICY_PROBE(4)
NATIONAL_POLICY_PROBE(5)
#undef NATIONAL_POLICY_PROBE

static bool factual_world_cup_row(const unsigned char *row) {
    if (u16_at(row,0x6c)!=2026 || u16_at(row,0x6a)!=2026 ||
        (u16_at(row,0x68)&0x1ff)!=200 || u16_at(row,0x74)!=0 ||
        u16_at(row,0x70)!=2026 || u16_at(row,0x72)!=2026) return false;
    const uint32_t expected[]={796,1649,765};
    for (unsigned rank=0;rank<3;++rank) {
        uintptr_t team=0;uint32_t uid=0;
        memcpy(&team,row+0x20+rank*8,8);
        if (!team || !readable_copy(&uid,(void *)(team+0xc),4) || uid!=expected[rank]) return false;
    }
    return true;
}

static bool admit_world_cup_fact_from_source(void) {
    if (world_cup_fact_admitted) return true;
    uintptr_t table=0,vector=0,bounds[2]={0};
    if (!comp_history_table_address ||
        !readable_copy(&table,(void *)comp_history_table_address,8) || !table ||
        !readable_copy(&vector,(void *)(table+0x88),8) || !vector ||
        !readable_copy(bounds,(void *)vector,16) || bounds[1]<=bounds[0] ||
        (bounds[1]-bounds[0])%8 || (bounds[1]-bounds[0])/8>1000000) return false;
    size_t count=(bounds[1]-bounds[0])/8;
    uintptr_t *rows=malloc(count*8),owner_found=0;
    unsigned matching=0;bool factual=false;
    unsigned char admitted[0x60]={0};
    if (!rows || !readable_copy(rows,(void *)bounds[0],count*8)) {free(rows);return false;}
    for (size_t i=0;i<count;++i) {
        unsigned char row[0x78];uintptr_t owner=0;uint32_t uid=0;
        if (!readable_copy(row,(void *)rows[i],sizeof row) || u16_at(row,0x6c)!=2026) continue;
        memcpy(&owner,row+0x18,8);
        if (!owner || !readable_copy(&uid,(void *)(owner+0xc),4) || uid!=1301385) continue;
        ++matching;
        factual=factual_world_cup_row(row);
        if (factual) {memcpy(admitted,row+0x18,sizeof admitted);owner_found=owner;}
    }
    free(rows);
    if (matching!=1 || !factual || !owner_found) return false;
    world_cup_source_owner=owner_found;
    memcpy(world_cup_factual_history,admitted,sizeof admitted);
    world_cup_fact_admitted=true;
    if (audit) {fputs("WORLD_CUP_FACT_ADMITTED unique=1 edition=2026 date=2026/200 podium=796/1649/765\n",audit);fflush(audit);}
    return true;
}

static bool factual_national_row(const unsigned char *row,const national_fact *f) {
    if (u16_at(row,0x6c)!=f->history_year || u16_at(row,0x6a)!=f->final_year ||
        (u16_at(row,0x68)&511)!=f->final_day || u16_at(row,0x74)!=0 ||
        u16_at(row,0x70)!=f->history_year || u16_at(row,0x72)!=f->history_year) return false;
    for (unsigned rank=0;rank<3;++rank) {
        uintptr_t team=0;uint32_t uid=0;memcpy(&team,row+0x20+rank*8,8);
        if (!f->podium[rank]) {if (team) return false;continue;}
        if (!team || !readable_copy(&uid,(void *)(team+0xc),4) || uid!=f->podium[rank]) return false;
    }
    return true;
}

static void admit_national_facts_from_source(void) {
    uintptr_t table=0,vector=0,bounds[2]={0};
    if (!comp_history_table_address ||
        !readable_copy(&table,(void *)comp_history_table_address,8) || !table ||
        !readable_copy(&vector,(void *)(table+0x88),8) || !vector ||
        !readable_copy(bounds,(void *)vector,16) || bounds[1]<=bounds[0] ||
        (bounds[1]-bounds[0])%8 || (bounds[1]-bounds[0])/8>1000000) return;
    size_t count=(bounds[1]-bounds[0])/8;
    uintptr_t *rows=malloc(count*8),owners[NATIONAL_FACT_COUNT]={0};
    unsigned matches[NATIONAL_FACT_COUNT]={0};
    if (!rows || !readable_copy(rows,(void *)bounds[0],count*8)) {free(rows);return;}
    for (size_t i=0;i<count;++i) {
        unsigned char row[0x78];uintptr_t owner=0;uint32_t uid=0;
        if (!readable_copy(row,(void *)rows[i],sizeof row)) continue;
        memcpy(&owner,row+0x18,8);
        if (!owner || !readable_copy(&uid,(void *)(owner+0xc),4)) continue;
        for (unsigned k=0;k<NATIONAL_FACT_COUNT;++k) {
            const national_fact *f=&national_facts[k];
            if (uid!=f->uid || u16_at(row,0x6c)!=f->history_year) continue;
            ++matches[k];
            if (factual_national_row(row,f)) owners[k]=owner;
        }
    }
    free(rows);
    for (unsigned k=0;k<NATIONAL_FACT_COUNT;++k) if (matches[k]==1 && owners[k]) {
        national_fact_owners[k]=owners[k];
        if (audit) fprintf(audit,"NATIONAL_FACT_ADMITTED uid=%u game_year=%u history_year=%u unique=1\n",
            national_facts[k].uid,national_facts[k].game_year,national_facts[k].history_year);
    }
    if (audit) fflush(audit);
}

static void inspect_world_cup_latest(const char *phase) {
    unsigned char comp[0xf8],latest[0x60];uint32_t uid=0;uintptr_t pointer=0;
    if (!audit || !world_cup_source_owner ||
        !readable_copy(comp,(void *)world_cup_source_owner,sizeof comp)) return;
    memcpy(&uid,comp+0xc,4);memcpy(&pointer,comp+0xa8,8);
    if (uid!=1301385 || !pointer || !readable_copy(latest,(void *)pointer,sizeof latest)) return;
    uint32_t podium[3]={0};
    for (unsigned rank=0;rank<3;++rank) {
        uintptr_t team=0;memcpy(&team,latest+8+rank*8,8);
        if (team) readable_copy(&podium[rank],(void *)(team+0xc),4);
    }
    fprintf(audit,"WORLD_CUP_LATEST phase=%s year=%u date=%u/%u podium=%u/%u/%u\n",phase,
        u16_at(latest,0x54),u16_at(latest,0x52),u16_at(latest,0x50)&0x1ff,
        podium[0],podium[1],podium[2]);fflush(audit);
}

static bool observe_world_cup_policy(void *self,const void *game_comp) {
    bool original=original_world_cup_policy(self,game_comp);
    if (!world_cup_history_mode || !world_cup_generation_ready ||
        !world_cup_fact_admitted || !game_comp) return original;
    uintptr_t source=0,database=0;uint32_t uid=0;uint16_t year=0,date[2]={0};
    if (!readable_copy(&source,(const char *)game_comp+0x138,8) || !source ||
        !readable_copy(&uid,(void *)(source+0xc),4) || uid!=1301385 ||
        !readable_copy(&year,(const char *)game_comp+0x248,2) || year!=2026 ||
        !comp_history_database_date_address ||
        !readable_copy(&database,(void *)comp_history_database_date_address,8) || !database ||
        !readable_copy(date,(void *)(database+0x144),4) || date[1]!=2026 ||
        (date[0]&0x1ff)<=200 ||
        source!=world_cup_source_owner) return original;
    bool skip=world_cup_history_mode==2;
    if (audit && world_cup_policy_observations++<12) {
        fprintf(audit,"WORLD_CUP_POLICY edition=2026 current=%u/%u native=%u skip_completed=%u caller=%p\n",
            date[1],date[0]&0x1ff,original,skip,__builtin_return_address(0));
        inspect_world_cup_latest("competition_year_policy");fflush(audit);
    }
    return skip?false:original;
}

static void inspect_comp_history_source(const char *phase) {
    if (!comp_history_diagnostics || !audit || !comp_history_table_address) return;
    inspect_world_cup_latest(phase);
    uintptr_t database=0;
    uint16_t database_date[2]={0};
    if (comp_history_database_date_address &&
        readable_copy(&database,(void *)comp_history_database_date_address,8) && database)
        readable_copy(database_date,(void *)(database+0x144),4);
    fprintf(audit,"COMP_HISTORY_DATABASE phase=%s date=%u/%u\n",phase,
        database_date[1],database_date[0]&0x1ff);
    uintptr_t table=0,vector=0,bounds[2]={0};
    if (!readable_copy(&table,(void *)comp_history_table_address,8) || !table ||
        !readable_copy(&vector,(void *)(table+0x88),8) || !vector ||
        !readable_copy(bounds,(void *)vector,16) || bounds[1]<bounds[0] ||
        (bounds[1]-bounds[0])%8 || (bounds[1]-bounds[0])/8>1000000) {
        fprintf(audit,"COMP_HISTORY_PROBE phase=%s unavailable_source_table\n",phase);
        fflush(audit);return;
    }
    size_t count=(bounds[1]-bounds[0])/8;
    uintptr_t *rows=malloc(count*8);
    if (!rows || !readable_copy(rows,(void *)bounds[0],count*8)) { free(rows);return; }
    unsigned found=0;
    for (size_t i=0;i<count;++i) {
        unsigned char row[0x78],comp[0xf8];uintptr_t owner=0;
        if (!readable_copy(row,(void *)rows[i],sizeof row)) continue;
        memcpy(&owner,row+0x18,8);
        if (!readable_copy(comp,(void *)owner,sizeof comp)) continue;
        uint32_t uid;memcpy(&uid,comp+0xc,4);
        bool known=uid==1301385;
        for (unsigned k=0;k<6;++k) if (uid==national_competition_uids[k]) known=true;
        if (!known || u16_at(row,0x6c)<2022) continue;
        uint32_t placings[3]={0};
        for (unsigned rank=0;rank<3;++rank) {
            uintptr_t team=0;memcpy(&team,row+0x20+8*rank,8);
            if (team) readable_copy(&placings[rank],(void *)(team+0xc),4);
        }
        uintptr_t latest=0;memcpy(&latest,comp+0xa8,8);
        fprintf(audit,"COMP_HISTORY_SOURCE phase=%s uid=%u year=%u date=%u/%u flags=%u start=%u end=%u podium=%u/%u/%u selected_latest=%u competition_type=%u\n",
            phase,uid,u16_at(row,0x6c),u16_at(row,0x6a),u16_at(row,0x68)&0x1ff,
            u16_at(row,0x74),u16_at(row,0x70),u16_at(row,0x72),
            placings[0],placings[1],placings[2],latest==rows[i]+0x18,comp[0xf4]);
        ++found;
    }
    free(rows);
    fprintf(audit,"COMP_HISTORY_PROBE phase=%s source_rows=%zu national_recent_rows=%u data_changes=0\n",phase,count,found);
    fflush(audit);
}

static void observe_comp_history_init(void *self, unsigned mode) {
    inspect_comp_history_source("before_native_linking");
    original_comp_history_init(self,mode);
    inspect_comp_history_source("after_native_linking");
}

// The live game normally calls this manager wrapper, which calls the same
// initializer directly and then clears the source table. Observing only the
// initializer's own vtable misses that direct call. Preserve the entire native
// wrapper and its pointer-width second argument without reimplementing it.
static void observe_comp_history_wrapper(void *self, uintptr_t argument) {
    // Admission is required operation, independent of diagnostic logging.
    // Reset here too: never retain a fact if another load omits this seed.
    reset_world_cup_generation();
    if (world_cup_history_mode) admit_world_cup_fact_from_source();
    if (international_history_mode) admit_national_facts_from_source();
    if (international6_mode) international6_admit(self);
    inspect_comp_history_source("before_native_manager_wrapper");
    original_comp_history_wrapper(self,argument);
    if (international6_mode) international6_linked(self);
    world_cup_generation_ready=world_cup_fact_admitted;
    if (international_history_mode) for (unsigned k=0;k<NATIONAL_FACT_COUNT;++k)
        if (national_fact_owners[k]) national_generation_ready=true;
    inspect_comp_history_source("after_native_manager_wrapper");
    if (audit && world_cup_history_mode) {
        fprintf(audit,"WORLD_CUP_GENERATION generation=%u ready=%u\n",
            world_cup_generation,world_cup_generation_ready);fflush(audit);
    }
}

static void observe_comp_history_finalize(void *self) {
    // Called from the end of the native initializer, before the manager
    // wrapper clears the table. This reveals which row was selected latest.
    inspect_comp_history_source("native_linking_complete_before_cleanup");
    original_comp_history_finalize(self);
}

static bool matching_uuid(const struct mach_header_64 *header) {
    static const unsigned char expected[16] = {
        0xd7,0x10,0xf6,0xfa,0x6a,0xca,0x32,0xbb,
        0x99,0xfe,0x45,0x1c,0xee,0x8d,0xfa,0x3d
    };
    if (!header || header->magic != MH_MAGIC_64 || header->cputype != CPU_TYPE_ARM64)
        return false;
    const unsigned char *p = (const unsigned char *)(header + 1);
    for (unsigned i = 0; i < header->ncmds; ++i) {
        const struct load_command *command = (const struct load_command *)p;
        if (command->cmd == LC_UUID)
            return memcmp(((const struct uuid_command *)p)->uuid, expected, 16) == 0;
        if (command->cmdsize < sizeof *command)
            return false;
        p += command->cmdsize;
    }
    return false;
}

static bool writable_data_pointer(uintptr_t address, uintptr_t replacement) {
    mach_vm_address_t region = address;
    mach_vm_size_t length = 0;
    vm_region_basic_info_data_64_t info;
    mach_msg_type_number_t count = VM_REGION_BASIC_INFO_COUNT_64;
    mach_port_t object = MACH_PORT_NULL;
    kern_return_t status = mach_vm_region(mach_task_self(), &region, &length,
        VM_REGION_BASIC_INFO_64, (vm_region_info_t)&info, &count, &object);
    if (object != MACH_PORT_NULL)
        mach_port_deallocate(mach_task_self(), object);
    if (status != KERN_SUCCESS || address < region || address + sizeof(uintptr_t) > region + length ||
        (info.protection & VM_PROT_EXECUTE)) {
        if (audit) fprintf(audit, "ERROR invalid data region status=%d\n", status);
        return false;
    }
    const mach_vm_size_t pagesize = vm_page_size;
    const mach_vm_address_t page = address & ~(pagesize - 1);
    uintptr_t previous = atomic_load((_Atomic uintptr_t *)address);
    status = mach_vm_protect(mach_task_self(), page, pagesize, false,
        VM_PROT_READ | VM_PROT_WRITE | VM_PROT_COPY);
    if (status != KERN_SUCCESS) {
        if (audit) fprintf(audit, "ERROR data protection status=%d\n", status);
        return false;
    }
    atomic_store_explicit((_Atomic uintptr_t *)address, replacement, memory_order_release);
    status = mach_vm_protect(mach_task_self(), page, pagesize, false, info.protection);
    if (status != KERN_SUCCESS) {
        // Restore the dispatch before returning failure; never leave a partial hook.
        atomic_store((_Atomic uintptr_t *)address, previous);
        mach_vm_protect(mach_task_self(), page, pagesize, false, info.protection);
        if (audit) fprintf(audit, "ERROR restoring data protection status=%d\n", status);
        return false;
    }
    return true;
}

__attribute__((constructor)) static void initialize(void) {
    const char *path = getenv("FM24_AWARDS_LOG");
    audit = path && *path ? fopen(path, "a") : stderr;
    uint32_t image = UINT32_MAX;
    for (uint32_t i = 0; i < _dyld_image_count(); ++i) {
        const struct mach_header_64 *header = (const struct mach_header_64 *)_dyld_get_image_header(i);
        if (matching_uuid(header)) { image = i; break; }
    }
    if (image == UINT32_MAX) {
        if (audit) {
            fprintf(audit, "DISABLED pid=%d unsupported executable UUID or architecture\n", getpid());
            const struct mach_header_64 *h = (const struct mach_header_64 *)_dyld_get_image_header(0);
            fprintf(audit, "IMAGE0 name=%s magic=%x cpu=%x commands=%u\n",
                _dyld_get_image_name(0), h->magic, h->cputype, h->ncmds);
            if (h->magic == MH_MAGIC_64) {
                const unsigned char *p = (const unsigned char *)(h+1);
                for (unsigned i=0; i<h->ncmds; ++i) {
                    const struct load_command *c = (const struct load_command *)p;
                    if (c->cmd == LC_UUID) {
                        const unsigned char *u = ((const struct uuid_command *)p)->uuid;
                        fputs("UUID0=", audit);
                        for(unsigned j=0;j<16;++j) fprintf(audit,"%02x",u[j]);
                        fputc('\n',audit);
                    }
                    if(c->cmdsize < sizeof *c) break;
                    p += c->cmdsize;
                }
            }
            fflush(audit);
        }
        return;
    }
    intptr_t slide = _dyld_get_image_vmaddr_slide(image);
    uintptr_t slot = 0x1050f92b8ULL + slide;
    uintptr_t entry = 0x101b317b8ULL + slide;
    static const unsigned char dispatch_bytes[] = {
        0x00,0x20,0x00,0x91,0x21,0x00,0x40,0xf9,0x1c,0x00,0x00,0x14
    };
    static const unsigned char continuation_bytes[] = {
        0xe0,0x03,0x17,0xaa,0x3e,0xf4,0x5e,0x94,0xf6,0x13,0x00,0xf9
    };
    if (*(uintptr_t *)slot != entry || memcmp((void *)entry, dispatch_bytes, sizeof dispatch_bytes) ||
        memcmp((void *)(0x101b31b14ULL+slide), continuation_bytes, sizeof continuation_bytes)) {
        if (audit) { fprintf(audit, "DISABLED executable layout mismatch\n"); fflush(audit); }
        return;
    }
    original_dispatch = (conversion_dispatch)entry;
    native_history_info=(uint16_t (*)(const void *,unsigned))(0x103a13f9cULL+slide);
    fm24_native_get_manager = 0x101420bb8ULL + slide;
    fm24_native_cache_address = 0x10526a780ULL + slide;
    fm24_native_continuation = 0x101b31b14ULL + slide;
    if (!writable_data_pointer(slot, (uintptr_t)dispatch)) {
        if (audit) fflush(audit);
        return;
    }
    if (audit) {
        fprintf(audit, "ENABLED FM24-arm64 UUID=d710f6fa-6aca-32bb-99fe-451cee8dfa3d editions=18 disk_changes=0 code_changes=0\n");
        fflush(audit);
    }
    const char *comp_probe=getenv("FM24_COMP_HISTORY_PROBE");
    const char *world_mode=getenv("FM24_WORLD_CUP_HISTORY_MODE");
    const char *international_mode=getenv("FM24_INTERNATIONAL_HISTORY_MODE");
    const char *international6_env=getenv("FM24_INTERNATIONAL6_HISTORY_MODE");
    international6_mode=international6_env && !strcmp(international6_env,"observe")?1:
        international6_env && !strcmp(international6_env,"skip-completed")?2:0;
    if (international6_env && *international6_env && !international6_mode && audit) {
        fputs("INTERNATIONAL6_MODE_REJECTED valid_modes=observe,skip-completed apply=0\n",audit);fflush(audit);
    }
    world_cup_history_mode=world_mode && !strcmp(world_mode,"observe")?1:
        world_mode && !strcmp(world_mode,"skip-completed")?2:0;
    international_history_mode=international_mode && !strcmp(international_mode,"observe")?1:
        international_mode && !strcmp(international_mode,"skip-completed")?2:0;
    comp_history_diagnostics=comp_probe && !strcmp(comp_probe,"1");
    if (comp_history_diagnostics || world_cup_history_mode || international_history_mode || international6_mode) {
        comp_history_table_address=0x105302868ULL+slide;
        comp_history_database_date_address=0x1053038f8ULL+slide;
    }
    if (world_cup_history_mode || international_history_mode || international6_mode) {
        uintptr_t init_slot=0x1050e13f8ULL+slide,init_entry=0x10144cc54ULL+slide;
        uintptr_t wrapper_slot=0x1050e1408ULL+slide,wrapper_entry=0x10144d708ULL+slide;
        static const unsigned char init_signature[]={0xff,0xc3,0x01,0xd1,0xf8,0x5f,0x03,0xa9};
        static const unsigned char wrapper_signature[]={0xfd,0x7b,0xbf,0xa9,0xfd,0x03,0x00,0x91};
        bool enabled=false;
        if (*(uintptr_t *)init_slot==init_entry &&
            !memcmp((void *)init_entry,init_signature,sizeof init_signature) &&
            *(uintptr_t *)wrapper_slot==wrapper_entry &&
            !memcmp((void *)wrapper_entry,wrapper_signature,sizeof wrapper_signature)) {
            original_comp_manager_init=(void (*)(void *))init_entry;
            original_comp_history_wrapper=(void (*)(void *,uintptr_t))wrapper_entry;
            enabled=writable_data_pointer(init_slot,(uintptr_t)observe_comp_manager_init) &&
                writable_data_pointer(wrapper_slot,(uintptr_t)observe_comp_history_wrapper);
        }
        if (!enabled) {world_cup_history_mode=0;international_history_mode=0;international6_mode=0;}
        if (audit) {fprintf(audit,"WORLD_CUP_LIFECYCLE enabled=%u\n",enabled);fflush(audit);}
    }
    if (world_cup_history_mode) {
        uintptr_t policy_slot=0x10523cdb8ULL+slide,policy_entry=0x1040eb19cULL+slide;
        static const unsigned char policy_signature[]={0xf6,0x57,0xbd,0xa9,0xf4,0x4f,0x01,0xa9};
        if (*(uintptr_t *)policy_slot==policy_entry &&
            !memcmp((void *)policy_entry,policy_signature,sizeof policy_signature)) {
            original_world_cup_policy=(bool (*)(void *,const void *))policy_entry;
            bool enabled=writable_data_pointer(policy_slot,(uintptr_t)observe_world_cup_policy);
            if (audit) {fprintf(audit,"WORLD_CUP_POLICY_ENABLED mode=%d enabled=%u\n",world_cup_history_mode,enabled);fflush(audit);}
        }
    }
    if (comp_history_diagnostics || international_history_mode || international6_mode) {
        uintptr_t actual_slot=0x10521c748ULL+slide,actual_entry=0x103c18fe8ULL+slide;
        static const unsigned char actual_signature[]={0xff,0xc3,0x02,0xd1,0xe9,0x23,0x06,0x6d};
        bool enabled=false;
        if (*(uintptr_t *)actual_slot==actual_entry &&
            !memcmp((void *)actual_entry,actual_signature,sizeof actual_signature)) {
            original_actual_comp_policy=(national_year_policy)actual_entry;
            enabled=writable_data_pointer(actual_slot,(uintptr_t)observe_actual_comp_policy);
        }
        if (audit) fprintf(audit,"ACTUAL_COMP_POLICY_ENABLED mode=%d enabled=%u\n",international_history_mode,enabled);
        if (!enabled) {international_history_mode=0;international6_mode=0;}
    }
    if (international6_mode && !international6_install(slide)) international6_mode=0;
    if (comp_history_diagnostics) {
        const uintptr_t national_slots[]={0x10523d4b0ULL,0x10523dab0ULL,0x10523e0b0ULL,
            0x10523e6b0ULL,0x10523eeb0ULL,0x105240ab0ULL};
        const uintptr_t national_entries[]={0x1040f377cULL,0x1040f8424ULL,0x1040f8c94ULL,
            0x1040feb34ULL,0x103c18fe8ULL,0x103c18fe8ULL};
        static const unsigned char national_signatures[][8]={
            {0x08,0x90,0x44,0x79,0x68,0x01,0x00,0x36},
            {0x08,0x90,0x44,0x79,0xaa,0x8c,0x00,0xd0},
            {0x08,0x90,0x44,0x79,0xaa,0x8c,0x00,0xd0},
            {0x08,0x90,0x44,0x79,0x8a,0x8c,0x00,0x90},
            {0xff,0xc3,0x02,0xd1,0xe9,0x23,0x06,0x6d},
            {0xff,0xc3,0x02,0xd1,0xe9,0x23,0x06,0x6d}};
        const national_year_policy probes[]={national_policy_probe_0,national_policy_probe_1,
            national_policy_probe_2,national_policy_probe_3,national_policy_probe_4,national_policy_probe_5};
        for (unsigned k=0;k<6;++k) {
            uintptr_t slot=national_slots[k]+slide,entry=national_entries[k]+slide;
            if (*(uintptr_t *)slot==entry && !memcmp((void *)entry,national_signatures[k],8)) {
                original_national_policies[k]=(national_year_policy)entry;
                bool enabled=writable_data_pointer(slot,(uintptr_t)probes[k]);
                if (audit) fprintf(audit,"NATIONAL_POLICY_PROBE_ENABLED uid=%u enabled=%u\n",
                    national_competition_uids[k],enabled);
            }
        }
        uintptr_t comp_slot=0x10521d310ULL+slide,comp_entry=0x103c775b4ULL+slide;
        uintptr_t wrapper_slot=0x1050e1408ULL+slide,wrapper_entry=0x10144d708ULL+slide;
        uintptr_t finalize_slot=0x1050e1448ULL+slide,finalize_entry=0x10145295cULL+slide;
        static const unsigned char signature[]={0xff,0xc3,0x04,0xd1,0xe9,0x23,0x0c,0x6d};
        static const unsigned char wrapper_signature[]={0xfd,0x7b,0xbf,0xa9,0xfd,0x03,0x00,0x91};
        static const unsigned char finalize_signature[]={0x08,0x9f,0x95,0x52,0x00,0x68,0x68,0xf8};
        if (*(uintptr_t *)comp_slot==comp_entry && !memcmp((void *)comp_entry,signature,sizeof signature) &&
            (*(uintptr_t *)wrapper_slot==wrapper_entry ||
             *(uintptr_t *)wrapper_slot==(uintptr_t)observe_comp_history_wrapper) &&
            !memcmp((void *)wrapper_entry,wrapper_signature,sizeof wrapper_signature) &&
            *(uintptr_t *)finalize_slot==finalize_entry &&
            !memcmp((void *)finalize_entry,finalize_signature,sizeof finalize_signature)) {
            original_comp_history_init=(void (*)(void *,unsigned))comp_entry;
            original_comp_history_wrapper=(void (*)(void *,uintptr_t))wrapper_entry;
            original_comp_history_finalize=(void (*)(void *))finalize_entry;
            if (writable_data_pointer(comp_slot,(uintptr_t)observe_comp_history_init)) {
                comp_history_table_address=0x105302868ULL+slide;
                comp_history_database_date_address=0x1053038f8ULL+slide;
                bool wrapper_enabled=writable_data_pointer(wrapper_slot,(uintptr_t)observe_comp_history_wrapper);
                bool finalize_enabled=writable_data_pointer(finalize_slot,(uintptr_t)observe_comp_history_finalize);
                if (audit) { fprintf(audit,"COMP_HISTORY_PROBE_ENABLED mode=read_only manager_wrapper=%u finalizer=%u\n",wrapper_enabled,finalize_enabled);fflush(audit); }
            }
        }
    }
    // Both extra slots and the native routine must match this exact build.
    uintptr_t load_slot = 0x1050d84d8ULL + slide;
    uintptr_t manager_slot = 0x1050f9160ULL + slide;
    uintptr_t secondary_slot = 0x1050f9188ULL + slide;
    if (*(uintptr_t *)load_slot != 0x10132f5a8ULL+slide ||
        *(uintptr_t *)manager_slot != 0x101b24180ULL+slide ||
        *(uintptr_t *)secondary_slot != 0x101b25700ULL+slide) {
        if (audit) { fputs("SCHEDULE_DISABLED vtable mismatch\n",audit); fflush(audit); }
        return;
    }
    const char *mode = getenv("FM24_AWARDS_SCHEDULE_MODE");
    const char *first_mode = getenv("FM24_AWARDS_FIRST_CYCLE_MODE");
    recover_first_ceremony=first_mode && strcmp(first_mode,"catchup")==0;
    schedule_mode = mode && strcmp(mode,"observe")==0 ? 1 :
                    mode && strcmp(mode,"apply")==0 ? 2 : 0;
    if (!schedule_mode) return;
    native_current_date = (const uint16_t *)(0x10528cc28ULL+slide);
    native_period_calculator = (void (*)(void *))(0x10130b274ULL+slide);
    year_vptr = 0x1050d84c0ULL+slide;
    original_year_load = (year_loader)*(uintptr_t *)load_slot;
    original_manager_handler = (manager_handler)*(uintptr_t *)manager_slot;
    if (!writable_data_pointer(load_slot,(uintptr_t)load_year)) {
        schedule_mode=0;
        return;
    }
    if (!writable_data_pointer(manager_slot,(uintptr_t)manager_event)) {
        writable_data_pointer(load_slot,(uintptr_t)original_year_load);
        schedule_mode=0;
        return;
    }
    if (!writable_data_pointer(secondary_slot,(uintptr_t)manager_secondary_event)) {
        writable_data_pointer(manager_slot,(uintptr_t)original_manager_handler);
        writable_data_pointer(load_slot,(uintptr_t)original_year_load);
        schedule_mode=0;
        return;
    }
    if (audit) {
        fprintf(audit,"SCHEDULE_ENABLED mode=%s known_awards=%lu first_cycle=%s\n",mode,
            (unsigned long)(sizeof fixed_award_uids/sizeof *fixed_award_uids),
            recover_first_ceremony?"catchup":"defer");
        fflush(audit);
    }
}

__attribute__((destructor)) static void finish(void) {
    if (audit) {
        fprintf(audit, "EXIT imported_rows=%u schedule_proposals=%u schedule_changes=%u manager_events=%u time_events=%u\n",
                converted,schedule_observed,schedule_changed,manager_events,time_events);
        if (audit != stderr) fclose(audit);
    }
}
