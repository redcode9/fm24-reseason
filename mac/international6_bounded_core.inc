/* Isolated bounded canary. Six observed policy years only; no source edits.
 * Runtime acceptance, including the NL season-to-history mapping, still needs
 * the next new-career full getter audit. No general year transformation here.
 */
typedef bool (*international6_native_policy)(void *);
typedef struct {
    uint32_t uid;
    uint16_t history_year,start_year,end_year,final_year,final_day,game_year;
    uint32_t podium[3];
} international6_fact;
static const international6_fact international6_facts[]={
    {121092,2023,2023,2023,2023,356,2023,{679,323,106756}},
    {121092,2025,2025,2025,2025,194,2025,{630,868,0}},
    {145509,2025,2025,2025,2025,187,2025,{379,390,0}},
    {129986,2024,2024,2024,2024,182,2024,{1438,1443,1441}},
    {222981,2024,2023,2024,2024,84,2023,{390,379,377}},
    {222981,2025,2024,2025,2025,82,2024,{379,382,364}}
};
#define INTERNATIONAL6_COUNT (sizeof international6_facts/sizeof *international6_facts)
static const uint32_t international6_uids[]={121092,145509,129986,222981};
typedef struct {
    unsigned char row[0x78];
    uint32_t uid,podium[3];
    unsigned podium_known;
} international6_source_snapshot;
typedef struct {
    uintptr_t source,vptr;
    uint32_t uid;
    uint16_t year;
    unsigned generation;
    bool valid;
} international6_policy_input;
static struct {
    uintptr_t owners[INTERNATIONAL6_COUNT],database,manager;
    unsigned matches[INTERNATIONAL6_COUNT],exact[INTERNATIONAL6_COUNT];
    unsigned generation;
    bool ready,complete;
} international6_state;
static international6_native_policy international6_original_cwc,international6_original_gold;
static unsigned international6_policy_logged[3][4];
#ifdef FM24_INTERNATIONAL6_HARNESS
static void (*international6_test_before_verify)(void);
#endif

static unsigned international6_uid_index(uint32_t uid) {
    for (unsigned k=0;k<4;++k) if (international6_uids[k]==uid) return k;
    return 4;
}
static void international6_reset(void) {
    memset(&international6_state,0,sizeof international6_state);
    memset(international6_policy_logged,0,sizeof international6_policy_logged);
}
static bool international6_source_row(const unsigned char *row,const international6_fact *f) {
    if (u16_at(row,0x6c)!=f->history_year || u16_at(row,0x6a)!=f->final_year ||
        (u16_at(row,0x68)&511)!=f->final_day || u16_at(row,0x70)!=f->start_year ||
        u16_at(row,0x72)!=f->end_year || u16_at(row,0x74)!=0) return false;
    for (unsigned rank=0;rank<3;++rank) {
        uintptr_t team=0;uint32_t uid=0;memcpy(&team,row+0x20+rank*8,8);
        if (!f->podium[rank]) {if (team) return false;continue;}
        if (!team || !readable_copy(&uid,(void *)(team+0xc),4) || uid!=f->podium[rank]) return false;
    }
    return true;
}
static bool international6_database(uintptr_t *db,uint16_t today[2]) {
    return comp_history_database_date_address &&
        readable_copy(db,(void *)comp_history_database_date_address,8) && *db &&
        readable_copy(today,(void *)(*db+0x144),4) && today[1]==2026 &&
        (today[0]&511)>=1 && (today[0]&511)<=365;
}
static void international6_failure(const char *reason,size_t index,uintptr_t row,uintptr_t owner,unsigned *samples) {
    if (audit && (*samples)++<8)
        fprintf(audit,"INTERNATIONAL6_SOURCE_FAULT reason=%s index=%zu row=%p owner=%p admission=0\n",
            reason,index,(void *)row,(void *)owner);
}
static void international6_source_podium(international6_source_snapshot *s) {
    s->podium_known=0;
    for (unsigned rank=0;rank<3;++rank) {
        uintptr_t team=0;memcpy(&team,s->row+0x20+rank*8,8);s->podium[rank]=0;
        if (!team || readable_copy(&s->podium[rank],(void *)(team+0xc),4))
            s->podium_known|=1U<<rank;
    }
}
static bool international6_context_unchanged(uintptr_t table,uintptr_t vector,const uintptr_t bounds[2],
        uintptr_t db,const uint16_t today[2],unsigned generation) {
    uintptr_t t=0,v=0,b[2]={0},d=0;uint16_t date[2]={0};
    return generation==world_cup_generation && international6_database(&d,date) && d==db &&
        !memcmp(date,today,4) && readable_copy(&t,(void *)comp_history_table_address,8) && t==table &&
        readable_copy(&v,(void *)(t+0x88),8) && v==vector &&
        readable_copy(b,(void *)v,16) && !memcmp(b,bounds,16);
}
static void international6_admit(void *manager) {
    international6_reset();
    uintptr_t table=0,vector=0,bounds[2]={0},db=0;uint16_t today[2]={0};
    unsigned generation=world_cup_generation;
    if (!international6_mode || !manager || !generation ||
        !international6_database(&db,today) || !comp_history_table_address ||
        !readable_copy(&table,(void *)comp_history_table_address,8) || !table ||
        !readable_copy(&vector,(void *)(table+0x88),8) || !vector ||
        !readable_copy(bounds,(void *)vector,16) || !bounds[0] || bounds[1]<=bounds[0] ||
        (bounds[1]-bounds[0])%8 || (bounds[1]-bounds[0])/8>1000000) {
        if (audit) {fputs("INTERNATIONAL6_SOURCE_INCOMPLETE reason=CONTEXT_OR_VECTOR admission=0\n",audit);fflush(audit);}
        return;
    }
    size_t count=(bounds[1]-bounds[0])/8;
    uintptr_t *rows=malloc(count*8),owners[INTERNATIONAL6_COUNT]={0},uid_owners[4]={0};
    international6_source_snapshot *snap=calloc(count,sizeof *snap);
    unsigned matches[INTERNATIONAL6_COUNT]={0},exact[INTERNATIONAL6_COUNT]={0},aliases[4]={0};
    unsigned null_row=0,unreadable_row=0,null_owner=0,unreadable_uid=0,changed=0;
    unsigned samples=0,null_samples=0,target_rows=0,dump_truncated=0;
    bool complete=true;
    if (!rows || !snap || !readable_copy(rows,(void *)bounds[0],count*8)) {
        free(rows);free(snap);
        if (audit) {fputs("INTERNATIONAL6_SOURCE_INCOMPLETE reason=ALLOCATION_OR_VECTOR_READ admission=0\n",audit);fflush(audit);}
        return;
    }
    if (audit) fprintf(audit,"INTERNATIONAL6_SOURCE_BEGIN phase=before_native_wrapper manager=%p database=%p generation=%u table=%p vector=%p begin=%p end=%p count=%zu\n",
        manager,(void *)db,generation,(void *)table,(void *)vector,(void *)bounds[0],(void *)bounds[1],count);
    for (size_t i=0;i<count;++i) {
        international6_source_snapshot *s=&snap[i];uintptr_t owner=0;
        if (!rows[i]) {++null_row;complete=false;international6_failure("NULL_ROW",i,0,0,&samples);continue;}
        if (!readable_copy(s->row,(void *)rows[i],sizeof s->row)) {
            ++unreadable_row;complete=false;international6_failure("UNREADABLE_ROW",i,rows[i],0,&samples);continue;
        }
        memcpy(&owner,s->row+0x18,8);
        /* Both SI linking passes explicitly skip a readable NULL owner.
         * Never treat NULL row, unreadable record or unreadable UID as empty. */
        if (!owner) {
            ++null_owner;
            if (audit && null_samples++<8) fprintf(audit,"INTERNATIONAL6_NULL_OWNER index=%zu row=%p history_year=%u packed_day=%u result_year=%u period=%u/%u flags=%u native_linker_ignores=1\n",
                i,(void *)rows[i],u16_at(s->row,0x6c),u16_at(s->row,0x68),u16_at(s->row,0x6a),u16_at(s->row,0x70),u16_at(s->row,0x72),u16_at(s->row,0x74));
            continue;
        }
        if (!readable_copy(&s->uid,(void *)(owner+0xc),4)) {
            ++unreadable_uid;complete=false;international6_failure("UNREADABLE_OWNER_UID",i,rows[i],owner,&samples);continue;
        }
        unsigned index=international6_uid_index(s->uid);
        if (index==4) continue;
        ++target_rows;
        if (!uid_owners[index]) uid_owners[index]=owner;
        else if (uid_owners[index]!=owner) ++aliases[index];
        international6_source_podium(s);
        unsigned exact_mask=0;
        for (unsigned k=0;k<INTERNATIONAL6_COUNT;++k) {
            const international6_fact *f=&international6_facts[k];
            if (s->uid!=f->uid || u16_at(s->row,0x6c)!=f->history_year) continue;
            ++matches[k];
            if (international6_source_row(s->row,f)) {++exact[k];owners[k]=owner;exact_mask|=1U<<k;}
        }
        if (target_rows>4096) {++dump_truncated;complete=false;continue;}
        if (audit) {
            uintptr_t teams[3];memcpy(teams,s->row+0x20,24);
            fprintf(audit,"INTERNATIONAL6_SOURCE_ROW index=%zu row=%p owner=%p uid=%u history_year=%u packed_day=%u result_year=%u period=%u/%u flags=%u team_ptrs=%p/%p/%p podium=%u/%u/%u podium_known=%u exact_mask=%u generation=%u\n",
                i,(void *)rows[i],(void *)owner,s->uid,u16_at(s->row,0x6c),u16_at(s->row,0x68),u16_at(s->row,0x6a),u16_at(s->row,0x70),u16_at(s->row,0x72),u16_at(s->row,0x74),
                (void *)teams[0],(void *)teams[1],(void *)teams[2],s->podium[0],s->podium[1],s->podium[2],s->podium_known,exact_mask,generation);
        }
    }
    #ifdef FM24_INTERNATIONAL6_HARNESS
    if (international6_test_before_verify) international6_test_before_verify();
    #endif
    /* Second full read: compare raw records, every nonNULL owner UID and all
     * target TEAM bindings. No admitted fact survives a detected change. */
    if (complete) for (size_t i=0;i<count;++i) {
        international6_source_snapshot now={0};uintptr_t owner=0;
        bool stable=readable_copy(now.row,(void *)rows[i],sizeof now.row) && !memcmp(now.row,snap[i].row,sizeof now.row);
        if (stable) {
            memcpy(&owner,now.row+0x18,8);
            if (owner) stable=readable_copy(&now.uid,(void *)(owner+0xc),4) && now.uid==snap[i].uid;
            if (stable && international6_uid_index(now.uid)!=4) {
                international6_source_podium(&now);
                stable=now.podium_known==snap[i].podium_known && !memcmp(now.podium,snap[i].podium,sizeof now.podium);
            }
        }
        if (!stable) {++changed;complete=false;international6_failure("SOURCE_CHANGED_OR_SECOND_READ_FAILED",i,rows[i],owner,&samples);}
    }
    uintptr_t chunk[128];
    if (complete) for (size_t i=0;i<count;i+=128) {
        size_t n=count-i<128?count-i:128;
        if (!readable_copy(chunk,(void *)(bounds[0]+i*8),n*8) || memcmp(chunk,rows+i,n*8)) {
            ++changed;complete=false;international6_failure("VECTOR_CHANGED_OR_SECOND_READ_FAILED",i,0,0,&samples);break;
        }
    }
    if (!international6_context_unchanged(table,vector,bounds,db,today,generation)) {
        ++changed;complete=false;international6_failure("SOURCE_CONTEXT_CHANGED",0,0,0,&samples);
    }
    free(snap);free(rows);
    international6_state.complete=complete;
    international6_state.database=db;international6_state.manager=(uintptr_t)manager;international6_state.generation=generation;
    for (unsigned k=0;k<INTERNATIONAL6_COUNT;++k) {
        const international6_fact *f=&international6_facts[k];
        unsigned alias=aliases[international6_uid_index(f->uid)];
        international6_state.matches[k]=matches[k];international6_state.exact[k]=exact[k];
        if (complete && matches[k]==1 && exact[k]==1 && !alias) international6_state.owners[k]=owners[k];
        if (audit) fprintf(audit,"INTERNATIONAL6_SOURCE uid=%u history_year=%u game_year=%u period=%u/%u final=%u/%u matches=%u exact=%u owner_aliases=%u exact_unique=%u owner=%p generation=%u complete=%u\n",
            f->uid,f->history_year,f->game_year,f->start_year,f->end_year,f->final_year,f->final_day,
            matches[k],exact[k],alias,international6_state.owners[k]!=0,(void *)international6_state.owners[k],generation,complete);
    }
    if (audit) {
        fprintf(audit,"INTERNATIONAL6_SOURCE_CENSUS scanned=%zu null_row=%u unreadable_row=%u null_owner=%u unreadable_owner_uid=%u changed=%u target_rows=%u dump_truncated=%u complete=%u null_owner_rule=SI_TWO_PASS_SKIP\n",
            count,null_row,unreadable_row,null_owner,unreadable_uid,changed,target_rows,dump_truncated,complete);
        fflush(audit);
    }
}
static void international6_log_latest(unsigned k,const char *phase) {
    uintptr_t owner=international6_state.owners[k],latest=0;unsigned char payload[0x60];
    if (!audit || !owner) return;
    bool known=readable_copy(&latest,(void *)(owner+0xa8),8) && latest && readable_copy(payload,(void *)latest,sizeof payload);
    if (!known) {fprintf(audit,"INTERNATIONAL6_OWNER_LATEST phase=%s uid=%u owner=%p latest=%p readable=0\n",phase,international6_facts[k].uid,(void *)owner,(void *)latest);return;}
    international6_source_snapshot s={0};memcpy(s.row+0x18,payload,sizeof payload);international6_source_podium(&s);
    fprintf(audit,"INTERNATIONAL6_OWNER_LATEST phase=%s uid=%u owner=%p latest=%p readable=1 history_year=%u period=%u/%u packed_day=%u result_year=%u flags=%u podium=%u/%u/%u podium_known=%u\n",
        phase,international6_facts[k].uid,(void *)owner,(void *)latest,u16_at(payload,0x54),u16_at(payload,0x58),u16_at(payload,0x5a),u16_at(payload,0x50),u16_at(payload,0x52),u16_at(payload,0x5c),s.podium[0],s.podium[1],s.podium[2],s.podium_known);
}
static void international6_linked(void *manager) {
    uintptr_t db=0;uint16_t today[2]={0};
    international6_state.ready=international6_mode && international6_state.complete &&
        international6_state.generation==world_cup_generation &&
        international6_state.manager==(uintptr_t)manager &&
        international6_database(&db,today) && db==international6_state.database;
    if (audit) {
        fprintf(audit,"INTERNATIONAL6_LINKED generation=%u ready=%u manager=%p source_vector_reread=0\n",world_cup_generation,international6_state.ready,manager);
        for (unsigned k=0;k<INTERNATIONAL6_COUNT;++k)
            if (!k || international6_facts[k].uid!=international6_facts[k-1].uid) international6_log_latest(k,"after_native_wrapper");
        fflush(audit);
    }
}
static bool international6_bound_source(unsigned k,uintptr_t source,uintptr_t db,const uint16_t today[2]) {
    const international6_fact *f=&international6_facts[k];
    return international6_mode && international6_state.ready && international6_state.complete &&
        international6_state.generation==world_cup_generation && international6_state.manager &&
        source && source==international6_state.owners[k] && db==international6_state.database &&
        today[1]==2026 && (today[0]&511)>=1 && (today[0]&511)<=365 &&
        (today[1]>f->final_year || (today[1]==f->final_year && (today[0]&511)>f->final_day));
}
static international6_policy_input international6_policy_read(void *self) {
    international6_policy_input p={0};p.generation=world_cup_generation;
    p.valid=self && readable_copy(&p.source,(char *)self+0x138,8) && p.source &&
        readable_copy(&p.uid,(void *)(p.source+0xc),4) &&
        readable_copy(&p.year,(char *)self+0x248,2) && readable_copy(&p.vptr,self,8);
    return p;
}
static bool international6_result(void *self,bool native,unsigned route,uintptr_t caller,const international6_policy_input *before) {
    if (!international6_mode || route>2) return native;
    international6_policy_input p=international6_policy_read(self);
    if (!p.valid) return native;
    unsigned index=international6_uid_index(p.uid);if (index==4) return native;
    bool stable=before && before->valid && before->source==p.source && before->uid==p.uid && before->year==p.year &&
        before->vptr==p.vptr && before->generation==p.generation;
    const uintptr_t expected_vptr[]={0x10521c6e0ULL,0x105243b80ULL,0x10523ec48ULL};
    bool type=p.vptr==expected_vptr[route]+international6_slide &&
        (p.uid==121092?route==1:(route==0 || (p.uid==145509 && route==2)));
    uintptr_t db=0;uint16_t today[2]={0};bool date=international6_database(&db,today);
    int fact=-1;
    for (unsigned k=0;k<INTERNATIONAL6_COUNT;++k)
        if (international6_facts[k].uid==p.uid && international6_facts[k].game_year==p.year) fact=(int)k;
    bool bound=fact>=0 && type && stable && date && international6_bound_source((unsigned)fact,p.source,db,today);
    bool skip=international6_mode==2 && native && bound;
    const char *reason=!stable?"POLICY_INPUT_CHANGED":!type?"TYPE_NOT_QUALIFIED":fact<0?"NON_TARGET_EDITION":
        !international6_state.complete?"SOURCE_CENSUS_INCOMPLETE":!international6_state.ready?"LINK_NOT_READY":
        !international6_state.owners[fact]?"SOURCE_NOT_EXACT_UNIQUE":!bound?"OWNER_DATABASE_DATE_OR_GENERATION":
        !native?"NATIVE_FALSE":international6_mode==1?"OBSERVE":"SKIP_EXACT_COMPLETED_SOURCE";
    bool result=skip?false:native;
    if (audit && international6_policy_logged[route][index]++<128) {
        fprintf(audit,"INTERNATIONAL6_BOUNDED_POLICY uid=%u game_year=%u history_year=%u route=%u vptr=%p source=%p exact_type=%u input_stable=%u native=%u returned=%u current=%u/%u generation=%u complete=%u ready=%u admitted=%u apply=%u mode=%d reason=%s caller=%p caller_unslid=%p mapping_basis=OBSERVED104_POLICY_AND_SOURCE_PERIOD canary_gameplay_proven=0\n",
            p.uid,p.year,fact<0?0:international6_facts[fact].history_year,route,(void *)p.vptr,(void *)p.source,type,stable,native,result,today[1],today[0]&511,
            world_cup_generation,international6_state.complete,international6_state.ready,bound,skip,international6_mode,reason,(void *)caller,(void *)(caller-international6_slide));
        fflush(audit);
    }
    return result;
}
static bool international6_cwc_policy(void *self) {
    uintptr_t caller=(uintptr_t)__builtin_return_address(0);
    international6_policy_input before=international6_policy_read(self);
    bool native=international6_original_cwc(self);
    return international6_result(self,native,1,caller,&before);
}
static bool international6_gold_policy(void *self) {
    uintptr_t caller=(uintptr_t)__builtin_return_address(0);
    international6_policy_input before=international6_policy_read(self);
    bool native=international6_original_gold(self);
    return international6_result(self,native,2,caller,&before);
}
static bool international6_install(intptr_t slide) {
    const uintptr_t slots[]={0x105243be8ULL,0x10523ecb0ULL};
    const uintptr_t entries[]={0x103c18fe8ULL,0x104104accULL};
    const unsigned char signatures[][16]={
        {0xff,0xc3,0x02,0xd1,0xe9,0x23,0x06,0x6d,0xf8,0x5f,0x07,0xa9,0xf6,0x57,0x08,0xa9},
        {0x08,0x90,0x44,0x79,0x4a,0x8c,0x00,0xd0,0x49,0x91,0x44,0x79,0x3f,0xa1,0x1f,0x71}};
    for (unsigned k=0;k<2;++k) if (*(uintptr_t *)(slots[k]+slide)!=entries[k]+slide ||
        memcmp((void *)(entries[k]+slide),signatures[k],16)) return false;
    international6_original_cwc=(international6_native_policy)(entries[0]+slide);
    international6_original_gold=(international6_native_policy)(entries[1]+slide);
    international6_slide=slide;
    bool cwc=writable_data_pointer(slots[0]+slide,(uintptr_t)international6_cwc_policy);
    bool gold=writable_data_pointer(slots[1]+slide,(uintptr_t)international6_gold_policy);
    if (audit) {fprintf(audit,"INTERNATIONAL6_BOUNDED_ENABLED cwc=%u gold=%u generic=1 mode=%d editions=6 gameplay_proven=0 source_changes=0\n",cwc,gold,international6_mode);fflush(audit);}
    return cwc && gold;
}
